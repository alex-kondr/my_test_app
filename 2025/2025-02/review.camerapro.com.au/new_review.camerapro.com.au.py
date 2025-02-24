from agent import *
from models.products import *


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.camerapro.com.au/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "level0")]')
    for cat in cats:
        name = cat.xpath('a/span/text()').string()

        sub_cats = cat.xpath('.//span[contains(., "Shop By Category")]/following-sibling::ul/li[contains(@class, "level1")]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('a/span/text()').string()

            sub_cats1 = sub_cat.xpath('.//ul[@class="category-links"]/li/a')
            if sub_cats1:
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('span/text()').string()
                    url = sub_cat1.xpath('@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
            else:
                url = sub_cat.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//li[contains(@class, "item product product-item")]')
    for prod in prods:
        name = prod.xpath('.//strong[contains(@class, "product-item-name")]/a/text()').string()
        url = prod.xpath('.//strong[contains(@class, "product-item-name")]/a/@href').string()

        revs = prod.xpath('.//a[@class="action view"]/text()')
        if revs:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@class="action next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].split('-')[0]
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[@class="product-company-logo"]/img/@alt').string()

    mpn = data.xpath('//div[@class="product attribute sku"]/div[@class="value"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//div[@data-th="GTIN/UPC Code"]/text()').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs_url = 'https://www.camerapro.com.au/review/product/listAjax/id/{}/'.format(product.ssid)
    session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//li[@class="item review-item"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//time/@datetime').string()

        author = rev.xpath('.//div[@class="review-author"]/p/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@itemprop="ratingValue"]/text()').string()
        if grade_overall:
            grade_overall = float(grade_overall.replace('%', '')) / 20
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.xpath('.//div[@class="review-title"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//div[@class="review-description"]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
