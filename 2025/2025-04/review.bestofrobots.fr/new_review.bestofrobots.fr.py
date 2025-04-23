from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.bestofrobots.fr/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@class="menu-full-width"]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    cats = data.xpath('//dl[contains(., "Catégorie")]//li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + name))

    if not cats:
        process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-title-block"]')
    for prod in prods:
        name = prod.xpath('.//h2[@class="product-name"]/a/text()').string()
        url = prod.xpath('.//h2[@class="product-name"]/a/@href').string()

        revs_cnt = prod.xpath('.//span[@class="number"]/text()').string()
        if revs_cnt and revs_cnt.isdigit() and int(revs_cnt) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url, revs_cnt=int(revs_cnt)))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="product"]/@value').string()
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//a[contains(@href, "/marque/")]/@title').string()

    mpn = data.xpath('//meta[@itemprop="sku"]/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    context['product'] = product

    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//li[@class="reviews__customers"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//span[@class="review-by"]/text()[last()]').string()
        if date:
            review.date = date.split()[-1]

        author = rev.xpath('.//span[@class="review-by"]/b/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grades = rev.xpath('.//div[@class="review_rating"]//tr')
        for grade in grades:
            grade_name = grade.xpath('.//span[@class="label"]/text()').string()
            grade_val = grade.xpath('.//div[@class="rating"]/@style').string()

            if grade_val:
                grade_val = grade_val.split()[-1].split('%')[0]
                if grade_val and grade_val.isdigit():
                    grade_val = float(grade_val) / 20

                    if grade_name:
                        review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))
                    else:
                        review.grades.append(Grade(type='overall', value=grade_val, best=5.0))

        is_verified_buyer = rev.xpath('.//img[contains(@src, "avisverifies")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.xpath('.//span[@class="review-title"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//div[@class="review_comment"]//div[not(@class)]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    offset = context.get('offset', 0) + 10
    next_page = context.get('page', 1) + 1
    if revs and offset < context['revs_cnt']:
        next_url = 'https://www.bestofrobots.fr/reviews?review_page={page}&pid={ssid}'.format(page=next_page, ssid=product.ssid)
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
