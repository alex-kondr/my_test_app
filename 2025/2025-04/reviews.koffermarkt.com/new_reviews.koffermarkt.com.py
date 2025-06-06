from agent import *
from models.products import *


XCAT = ['Marken', 'Sale %', 'Individuelle Schaumstoffe']


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.koffermarkt.com/', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="menu--container"]')
    for cat in cats:
        name = cat.xpath('div[@class="button-container"]/a//text()').string(multiple=True).replace('Zur Kategorie', '').strip()

        if name not in XCAT:
            sub_cats = cat.xpath('.//a[@class="menu--list-item-link"]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string()
                session.queue(Request(url + '?p=1&o=107&n=96', use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name + '|' + sub_name))
            else:
                url = cat.xpath('div[@class="button-container"]/a/@href').string()
                session.queue(Request(url + '?p=1&o=107&n=96', use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product--box box--minimal"]')
    for prod in prods:
        name = prod.xpath('.//a[@class="product--title"]//text()').string(multiple=True)
        url = prod.xpath('.//a[@class="product--title"]/@href').string()

        rating = prod.xpath('.//i[@class="icon--star"]')
        if rating:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url))
        else:
            return

    next_url = data.xpath('//a[@title="Nächste Seite"]/@href').string()
    if next_url:
        session.queue(Request(next_url + '&o=107&n=96', use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name'].replace(u'\x9F', '').strip()
    product.url = context['url']
    product.ssid = data.xpath('//meta[@itemprop="productID"]/@content').string()
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[@itemprop="brand"]/@content').string()

    mpn = data.xpath('//span[@itemprop="sku"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//tr[contains(., "EAN-Code")]/td[@class="product--properties-value"]/text()').string()
    if ean and ean.isdigit() and len(ean) > 12:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//meta[@itemprop="datePublished"]/@content').string()

        author = rev.xpath('.//span[@itemprop="author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//meta[@itemprop="ratingValue"]/@content').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//span[contains(., "Verifizierter Kauf")]')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.xpath('.//h4[@class="content--title"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[@itemprop="reviewBody"]//text()').string(multiple=True)
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
