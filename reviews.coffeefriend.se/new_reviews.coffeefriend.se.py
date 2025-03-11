from agent import *
from models.products import *


XCAT = ['Varumärken', 'Kampanjer']


def run(context, session):
    session.queue(Request('https://www.coffeefriend.se/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@id="menu-sv-meniu"]/li')
    for cat in cats:
        name = cat.xpath('span/span/a/text()').string()

        if name and name not in XCAT:
            sub_cats = cat.xpath('div[@class="sub-menu-container"]/ul[@class="dropdown-menu"]/li')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('span/span/span/text()').string()

                if sub_name not in XCAT:
                    sub_cats1 = sub_cat.xpath('.//ul[@class="dropdown-menu-deep"]/li//a')
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('text()').string()
                        url = sub_cat1.xpath('@href').string()

                        if not sub_name1.startswith('All') and 'Typ' not in sub_name:
                            session.queue(Request(url+'?orderby=reviews_count'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                        elif not sub_name1.startswith('All'):
                            session.queue(Request(url+'?orderby=reviews_count'), process_prodlist, dict(cat=name + '|' + sub_name1))


def process_prodlist(data, context, session):
    prods = data.xpath('//ul[contains(@class, "products")]/li')
    for prod in prods:
        name = prod.xpath('.//h2[contains(@class, "product__title")]//text()').string(multiple=True)
        url = prod.xpath('span//a/@href').string()

        revs_cnt = prod.xpath('.//span[@class="count"]/text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))
        else:
            return

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="gtm_item_id"]/@value').string()
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[contains(@class, "manufacturer")]/div[contains(@class, "value")]//text()').string(multiple=True)

    mpn = data.xpath('//input[@name="gtm_item_sku"]/@value').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//div[contains(@class, "ean_barcode")]/div[contains(@class, "value")]//text()').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    context['product'] = product
    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//ol[@class="commentlist"]/li')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('.//button/@data-id').string()

        date = rev.xpath('.//time/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//span[contains(@class, "author")]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//strong[@class="rating"]/text()').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        helpful = rev.xpath('.//button[contains(@class, "up")]/span/text()').string()
        if helpful and int(helpful) > 0:
            review.add_property(type='helpful_votes', value=int(helpful))

        not_helpful = rev.xpath('.//button[contains(@class, "down")]/span/text()').string()
        if not_helpful and int(not_helpful) > 0:
            review.add_property(type='not_helpful_votes', value=int(not_helpful))

        excerpt = rev.xpath('.//p[not(@class)]//text()').string()
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.do(Request(next_url), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
