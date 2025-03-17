from agent import *
from models.products import *
import simplejson


XCAT = ['Collections', 'Brands', 'Be Kind']
XSUBCAT = ['Shop by Colour', 'Shop by Brand', 'Gifts']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.browser.use_new_parser = True
    session.queue(Request('https://www.nailpolishdirect.co.uk/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//ul[@class='site-header__nav__285 site-header__nav__menu no-bullet']/li[contains(@class, 'drop-down')]")
    for cat in cats:
        name = cat.xpath("a//text()").string()

        if name not in XCAT:
            cats1 = cat.xpath('.//ul[contains(@class, "drop-down__menu__")]')
            for cat1 in cats1:
                name1 = cat1.xpath('li[@class="drop-down__title"]/span//text()').string()

                if name1 and name1 not in XCAT:
                    subcats = cat1.xpath(".//a[@class='top_level_link']")
                    for subcat in subcats:
                        subcat_name = subcat.xpath("span//text()").string()
                        url = subcat.xpath("@href").string()
                        session.queue(Request(url), process_category, dict(cat=name+"|"+name1+"|"+subcat_name))


def process_category(data, context, session):
    prods = data.xpath("//div[@class='product__details__title product__details__title--branded']/a")
    for prod in prods:
        name = prod.xpath("@title").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_category, dict(context))


def process_product(data, context, session):
    prod_json = simplejson.loads(data.xpath('//script[@type="application/ld+json"]//text()').string())

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = prod_json[0].get('Brand', {}).get('name')
    product.ssid = product.url.split('-')[-1]

    ean = prod_json[0].get('gtin13')
    if ean:
        product.add_property(type='id.ean', value=ean)

    sku = prod_json[0].get('SKU')
    if sku:
        product.sku = sku

    revs_ssid = product.ssid.replace('p', 'pr')
    revs_count = prod_json[0].get('aggregateRating', {}).get('reviewCount')
    if revs_count and int(revs_count) > 0:
        revs_url = product.url.replace(product.ssid, revs_ssid)
        session.queue(Request(revs_url), process_reviews, dict(product=product, revs_url=revs_url))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="product-reviews__ratings"]')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.title = rev.xpath('div[@class="product-reviews__star"]/span[@class="product-reviews__subtitle"]//text()').string()
        review.date = rev.xpath('.//meta/@content').string()

        author = rev.xpath('.//div[@itemprop="author"]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        is_verified = rev.xpath('.//div[@class="product-review__verified"]//text()').string()
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        is_recommended = rev.xpath('.//span[contains(text(), "Would you recommend this product?")]/following-sibling::text()[1]').string()
        if is_recommended and ('no' not in is_recommended.lower()):
            review.properties.append(ReviewProperty(value=True, type='is_recommended'))
        elif is_recommended and ('no' in is_recommended.lower()):
            review.properties.append(ReviewProperty(value=False, type='is_recommended'))

        grade_overall = rev.xpath('count(.//i[@class="ico icon-star"])')
        if grade_overall > 0:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        grades = rev.xpath('span[@class="product-reviews__subtitle"]')
        for grade in grades:
            grade_name = grade.xpath('text()').string()
            
            grade = grade.xpath('following-sibling::text()[1]').string().replace('-', '').strip()
            try:
                if 0 < float(grade) <= 5 and 'overall' not in grade_name.lower():
                    review.grades.append(Grade(name=grade_name, value=float(grade), best=5.0))
            except ValueError:
                break

        excerpt = rev.xpath('p[@itemprop="reviewBody"]//text()').string()
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    next_url = data.xpath('//div[@class="cms-page--reviews__pagination"]//a[@title="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_reviews, dict(context, product=product))

    elif product.reviews:
        session.emit(product)
