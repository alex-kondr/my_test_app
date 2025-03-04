from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.browser.use_new_parser = True
    session.queue(Request('https://www.nailpolishdirect.co.uk/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "drop-down--nav")]')
    for cat in cats:
        name = cat.xpath('a/text()').string(multiple=True)

        sub_cats = cat.xpath('.//ul[contains(@class, "drop-down__menu__categories")]//a')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('.//text()').string(multiple=True)
            url = sub_cat.xpath('@href').string()

            if ' All' not in sub_name:
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data. xpath('//a[@class="product__options__view"]')
    for prod in prods:
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = data.xpath('//span[@id="js-product-title"]/text()').string()
    product.url = context['url']
    product.ssid = product.url.split('-p')[-1]
    product.sku = product.ssid
    product.manufacturer = data.xpath('//span[@class="product-content__title--brand"]/text()').string()
    product.category = context['cat']

    mpn = data.xpath('//span[@id="js-product-reference"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    prod_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if prod_json:
        ean = simplejson.loads(prod_json).get('gtin13')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_cnt = data.xpath('//span[@class="review-count"]/text()').string()
    if revs_cnt and int(revs_cnt.strip('()')) > 0:
        revs_url = product.url.replace('-p' + product.ssid, '-pr' + product.ssid)
        session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="product-reviews__ratings"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//meta/@content').string()

        author = rev.xpath('.//div[@itemprop="author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//i[@class="ico icon-star"])')
        if grade_overall > 0:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        grades = rev.xpath('span[@class="product-reviews__subtitle"]')
        for grade in grades:
            grade_name = grade.xpath('text()').string()
            grade_val = grade.xpath('following-sibling::text()[1]').string().strip(' +-.\n\t')
            if grade_val.isdigit() and float(grade_val) > 0 and 'overall' not in grade_name.lower():
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))
            else:
                break

        is_verified = rev.xpath('.//div[@class="product-review__verified"]//text()').string()
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        is_recommended = rev.xpath('.//span[contains(text(), "Would you recommend this product?")]/following-sibling::text()[1]').string()
        if is_recommended and ('no' not in is_recommended.lower()):
            review.add_property(type='is_recommended', value=True)
        elif is_recommended and ('no' in is_recommended.lower()):
            review.add_property(type='is_recommended', value=False)

        title = rev.xpath('div[@class="product-reviews__star"]/span[@class="product-reviews__subtitle"]//text()').string()
        excerpt = rev.xpath('p[@itemprop="reviewBody"]//text()').string(multiple=True)
        if excerpt and len(excerpt.strip(' .+-\n\t')) > 1:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.strip(' .+-\n\t')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    next_url = data.xpath('//a[@title="next"]/@href').string()
    if next_url:
        session.do(Request(next_url), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
