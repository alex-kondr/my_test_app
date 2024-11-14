from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.helsebixen.dk/', use='curl'), process_category, dict())


def process_category(data, context, session):
    cats = data.xpath('//li/a[regexp:test(@class, "^navigation-offcanvas-link") and not(@title="Brands")]')
    for cat in cats:
        name = cat.xpath('@title').string()
        url = cat.xpath('@data-href').string()

        context['cat'] = (context.get('cat', '') + '|' + name).strip(' |')

        if url:
            url = 'https://www.helsebixen.dk' + url
            session.queue(Request(url), process_category, dict(context))
        else:
            url = cat.xpath('@href').string() + '?order=anmeldelser'
            session.queue(Request(url), process_prodlist, dict(context))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "card-body")]')
    for prod in prods:
        name = prod.xpath('.//a[contains(@class, "product-name")]/text()').string()
        url = prod.xpath('.//a[contains(@class, "product-name")]/@href').string()

        rating = prod.xpath('.//div[@class="product-review-point"]')
        if rating:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))
        else:
            return


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//meta[@itemprop="productID"]/@content').string()
    product.category = context['cat'].replace(' / ', '/')
    product.sku = data.xpath('//span[@itemprop="sku"]/text()').string()
    product.manufacturer = data.xpath('//a[contains(@class, "product-detail-manufacturer-link")]/@title').string()

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//body[p[contains(@class, "review")]]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//div[contains(@class, "review-item-date")]//text()').string(multiple=True)
        if date:
            review.date = date.rsplit(' ', 1)[0]

        author = rev.xpath('div[contains(@class, "review-item-info")]/p/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//div[contains(@class, "point-full")])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        is_verified_buyer = rev.xpath('.//small[contains(., "Verificeret køb")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.xpath('.//div[contains(@class, "review-item-title")]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[contains(@class, "review-item-content")]//text()').string(multiple=True)
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
