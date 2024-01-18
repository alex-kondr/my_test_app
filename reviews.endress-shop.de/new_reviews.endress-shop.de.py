from agent import *
from models.products import *


XCATS = ['ATV/UTV/Quads', 'KIOTI Kommunalmaschinen', ]


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.endress-shop.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="menu--container" and .//a[@title="Zur Kategorie Online-Shop"]]//a[@class="menu--list-item-link"]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCATS:
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product--box box--minimal"]')
    for prod in prods:
        name = prod.xpath('.//a[@class="product--title is--standard"]/text()').string()
        url = prod.xpath('.//a[@class="product--title is--standard"]/@href').string()

        rating = prod.xpath('.//span[@class="product--rating"]')
        if rating:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@aria-label="Nächste Seite"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1]
    product.category = context['cat']
    product.manufacturer = data.xpath('//span[@itemprop="supplierName"]/text()').string()
    product.sku = data.xpath('//span[@itemprop="sku"]/@content').string()

    mpn = data.xpath('//span[@itemprop="suppliernumber"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//meta[@itemprop="ean"]/@content').string()
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

        author = rev.xpath('.//span[@itemprop="author"]/span/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//meta[@itemprop="ratingValue"]/@content').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.xpath('.//h4[@class="content--title"]/text()').string()
        excerpt = rev.xpath('.//p[@itemprop="reviewBody"]/text()').string()
        if excerpt:
            review.title = title
            review.add_property(type='excerpt', value=excerpt)
        elif title:
            review.add_property(type='excerpt', value=title)

        if excerpt or title:
            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
