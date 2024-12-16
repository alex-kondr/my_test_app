from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.zwergperten-shop.de/axkid.html'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product--box")]')
    for prod in prods:
        name = prod.xpath('.//a[@class="product--title"]/@title').string()
        url = prod.xpath('.//a[@class="product--title"]/@href').string()
        sku = prod.xpath('@data-ordernumber').string()

        revs = prod.xpath('.//span[@class="product--rating"]')
        if revs:
            session.queue(Request(url), process_product, dict(context, name=name, url=url, sku=sku))

    # TODO: Check for next page


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = "Kinderprodukte"
    product.manufacturer = "Axkid"
    product.sku = context['sku']
    product.ssid = data.xpath('//meta[@itemprop="productID"]/@content').string()

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.title = rev.xpath('following::div[@class="entry--content"][1]/h4[@class="content--title"]//text()').string()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('following::head[2]//meta[@itemprop="datePublished"]/@content').string()

        author = rev.xpath('following::span[@itemprop="author"][1]/span[@itemprop="name"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('following::head[1]//meta[@itemprop="ratingValue"]/@content').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('following::div[@class="entry--content"][1]/p[@itemprop="reviewBody"]//text()').string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
