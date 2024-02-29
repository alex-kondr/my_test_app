from agent import *
from models.products import *


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.mytoolstore.de/kategorien/garten/'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product--box box--minimal"]')
    for prod in prods:
        name = prod.xpath('.//span[@class="product--title"]/text()').string()
        url = prod.xpath('a/@href').string()

        revs_cnt = prod.xpath('.//i[@class="icon--star"]')
        if revs_cnt:
            session.queue(Request(url), process_product, dict(name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict())


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.sku = data.xpath('//span[@itemprop="sku"]/text()').string()
    product.manufacturer = data.xpath('//meta[@itemprop="name"]/@content').string()

    category = data.xpath('//a[@class="breadcrumb--link"]/@title').strings()
    if category:
        product.category = '|'.join(category)
    else:
        product.category = 'Garten'

    mpn = data.xpath('//span[@itemprop="mpn"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//span[@itemprop="gtin13"]/text()').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    context['product'] = product
    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//meta[@itemprop="datePublished"]/@content').string()

        author = rev.xpath('.//span[@itemprop="name"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//meta[@itemprop="ratingValue"]/@content').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.xpath('.//h4[@class="content--title"]/text()').string()
        excerpt = rev.xpath('.//p[@itemprop="reviewBody"]//text()').string()
        if excerpt:
            review.title = title
        elif title:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
