from agent import *
from models.products import *


XCAT = ['Marken', 'Sale %', 'Individuelle Schaumstoffe']


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.koffermarkt.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="menu--container"]')
    for cat in cats:
        name = cat.xpath('div[@class="button-container"]/a//text()').string(multiple=True).replace('Zur Kategorie', '').strip()

        if name not in XCAT:
            sub_cats = cat.xpath('.//a[@class="menu--list-item-link"]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string()
                session.queue(Request(url + '?p=1&o=107&n=96'), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product--box box--minimal"]')
    for prod in prods:
        name = prod.xpath('.//a[@class="product--title"]//text()').string()
        url = prod.xpath('.//a[@class="product--title"]/@href').string()

        rating = prod.xpath('.//i[@class="icon--star"]')
        if rating:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))
        else:
            return

    next_url = data.xpath('//a[@title="Nächste Seite"]/@href').string()
    if next_url:
        session.queue(Request(next_url + '&o=107&n=96'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.replace('https://www.koffermarkt.com/', '')[:-1]
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[@itemprop="brand"]/@content').string()
    product.sku = data.xpath('//span[@itemprop="sku"]/text()').string()

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

        author = rev.xpath('.//span[@itemprop="author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//meta[@itemprop="ratingValue"]/@content').string()
        grade_worst = rev.xpath('.//meta[@itemprop="worstRating"]/@content').string()
        grade_best = rev.xpath('.//meta[@itemprop="bestRating"]/@content').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), worst=float(grade_worst), best=float(grade_best)))

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
