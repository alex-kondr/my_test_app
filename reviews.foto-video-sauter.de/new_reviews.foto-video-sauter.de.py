from agent import *
from models.products import *


XCAT = ['SALE', 'Aktionen', 'Second Hand', 'Ankauf', 'Workshops', 'Services']


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.foto-video-sauter.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//a[contains(@class, "nav-link main-navigation-link")]')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_category, dict(cat=name))


def process_category(data, context, session):
    sub_cats = data.xpath('//a[contains(@class, "inpage-navigation__category")]')
    for sub_cat in sub_cats:
        name = sub_cat.xpath('div[@class="inpage-navigation__title"]//text()').string(multiple=True)
        url = sub_cat.xpath('@href').string()
        session.queue(Request(url), process_category, dict(cat=context['cat'] + '|' + name))

    if not sub_cats:
        process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "card product-box")]')
    for prod in prods:
        ssid = prod.xpath('.//input[@name="product-id"]/@value').string()
        sku = prod.xpath('.//meta[@itemprop="sku"]/@content').string()
        mpn = prod.xpath('.//meta[@itemprop="mpn"]/@content').string()
        ean = prod.xpath('.//meta[@itemprop="gtin13"]/@content').string()
        manufacturer = prod.xpath('.//meta[@itemprop="name"]/@content').string()
        name = prod.xpath('.//a[@class="product-name"]/text()').string()
        url = prod.xpath('.//a[@class="product-name"]/@href').string()

        revs = prod.xpath('.//calumet-icon[@symbol="star-full" or @symbol="star-half"]')
        if revs:
            session.queue(Request(url), process_product, dict(context, ssid=ssid, sku=sku, mpn=mpn, ean=ean, manufacturer=manufacturer, name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = context['sku']
    product.category = context['cat']
    product.manufacturer = context['manufacturer']

    if context.get('mpn'):
        product.add_property(type='id.manufacturer', value=context['mpn'])

    if context.get('ean'):
        product.add_property(type='id.ean', value=context['ean'])

    revs = data.xpath('//div[@class="row review-item"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//div[contains(@class, "date")]//text()').string(multiple=True)

        author = rev.xpath('.//div[contains(@class, "content")]/p[not(@class)]//text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//calumet-icon[@symbol="star-full"]) + count(.//calumet-icon[@symbol="star-half"]) div 2')
        if grade_overall and grade_overall > 0:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.xpath('.//p[@class="h5"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[contains(@class, "content")]//text()').string(multiple=True)
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