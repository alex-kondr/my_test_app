from agent import  *
from models.products import *


XCAT = ['Sale!', 'ÜBER KAVALKADE', 'PARTNER']


def run(context, session):
    session.queue(Request('https://www.kavalkade.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "level1")]')
    for cat in cats:
        name = cat.xpath('a/span/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('.//li[contains(@class, "level2")]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a/span/text()').string()
                url = sub_cat.xpath('a/@href').string()
                session.queue(Request(url + '?product_list_limit=72'), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//a[@class="product-item-link"]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@class="action next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '')
    product.category = context['cat']

    context['product'] = product

    process_reviews(data, context,session)


def process_reviews(data, context, session):
    product = context['product']

    review = Review()
    review.type = 'user'
    review.url = product.url

    excerpt = data.xpath('//div[@id="product-review-container"]//text()').string(multiple=True)
    if excerpt and len(excerpt) > 1:
        review.add_property(type='excerpt', value=excerpt)

        review.ssid = review.digest() if author else review.digest(excerpt)

        product.reviews.append(review)

        session.emit(product)
