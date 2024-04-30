from agent import *
from models.products import *


XCAT = ['Marques', 'Fonctionnalités', 'Accessoires', 'Guide', 'Guides', 'Comparatifs', 'Marques / Gammes']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.bestofrobots.fr/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@class="menu-full-width"]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        sub_cats = cat.xpath('.//div[@class="sectiontitle"]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('.//text()').string(multiple=True)

            if sub_name not in XCAT:
                sub_cats1 = sub_cat.xpath('following-sibling::div[@class="section"][1]//a')
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('text()').string()
                    url = sub_cat1.xpath('@href').string()

                    if sub_name1:
                        session.queue(Request(url), process_prodlist, dict(cat = name + '|' + sub_name + '|' + sub_name1))
                else:
                    url = sub_cat.xpath('a/@href').string()

                    if url:
                        session.queue(Request(url), process_prodlist, dict(cat = name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//ol[@id="products-list"]/li')
    for prod in prods:
        name = prod.xpath('.//h2[@class="product-name"]/a/text()').string()
        url = prod.xpath('.//h2[@class="product-name"]/a/@href').string()

        rating = prod.xpath('.//div[@class="rating"]')
        if rating:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="product"]/@value').string()
    product.category = context['cat']
    product.sku = data.xpath('//meta[@itemprop="sku"]/@content').string()
    product.manufacturer = data.xpath('//meta[@itemprop="name"]/@content').string()

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs_cnt = data.xpath('//span[@itemprop="ratingCount"]/text()').string()
    if product.ssid and revs_cnt.isdigit() and int(revs_cnt) > 0:
        url = 'https://www.bestofrobots.fr/reviews?review_page=1&pid={}'.format(product.ssid)
        session.queue(Request(url), process_reviews, dict(product=product, revs_cnt=int(revs_cnt)))


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

        author = data.xpath('.//span[@class="review-by"]/b/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grades = data.xpath('.//div[@class="review_rating"]//tr')
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

        is_verified_buyer = data.xpath('.//img[contains(@src, "avisverifies")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = data.xpath('.//span[@class="review-title"]//text()').string(multiple=True)
        excerpt = data.xpath('.//div[@class="review_comment"]//text()').string(multiple=True)
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
    if offset < context['revs_cnt']:
        next_url = 'https://www.bestofrobots.fr/reviews?review_page={page}&pid={ssid}'.format(page=next_page, ssid=product.ssid)
        session.queue(Request(next_url), process_reviews, dict(context, product=product, page=next_page))

    elif product.reviews:
        session.emit(product)
