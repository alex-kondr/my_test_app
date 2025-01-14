from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.lizenzteufel.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="navigation-flyout"]//a[@class="nav-link"]')
    for cat in cats:
        name = cat.xpath('@title').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-info"]')
    for prod in  prods:
        name = prod.xpath('.//a[@class="product-name"]/text()').string()
        url = prod.xpath('.//a[@class="product-name"]/@href').string()

        rating = prod.xpath('.//span[@class="product-review-point"]')
        if rating:
            session.queue(Request(url), process_product, dict(context, url=url, name=name))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1]
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[@itemprop="name"]/@content').string()

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 11:
        product.add_property(type='id.ean', value=ean)

    mpn = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    context['product'] = product
    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="row product-detail-review-item-info"]')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.title = rev.xpath('.//div[@class="col-md-auto product-detail-review-item-title"]/p[@class]/text()').string()

        date = rev.xpath('div[@class="col-12 product-detail-review-item-date"]//small/text()').string()
        if date:
            review.date = ' '.join(date.split()[0:-1])

        author = rev.xpath('preceding::head[1]/meta[@itemprop="name"]/@content').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//span[@class="product-review-point"])')
        if grade_overall and grade_overall > 0:
            review.grades.append(Grade(type='overall', value=grade_overall/5, best=5.0))

        excerpt = rev.xpath('following-sibling::p[@class="product-detail-review-item-content"]/text()').string()
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
