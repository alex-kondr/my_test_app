from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.but.fr/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="niv1 closed"]//a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="category-carousel"]')
    for cat in cats:
        name = cat.xpath('.//h3//text()').string(multiple=True)

        sub_cats = cat.xpath('.//li[@class="splide__slide"]//a')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = sub_cat.xpath('@href').string().split('.html')[0] + '/NW-6272-avis-clients~1~etoile(s)/NW-6272-avis-clients~2~etoile(s)/NW-6272-avis-clients~3~etoile(s)/NW-6272-avis-clients~4~etoile(s)/NW-6272-avis-clients~5~etoile(s)'

            if sub_name not in [context['cat'], name]:
                cat = context['cat'] + '|' + name + '|' + sub_name
            else:
                cat = (context['cat'] + '|' + name)

            session.queue(Request(url), process_prodlist, dict(cat=cat))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product"]')
    for prod in prods:
        url = prod.xpath('.//a/@href').string()

        rating = prod.xpath('.//div[contains(@class, "infos-rating")]//text()').string()
        if rating:
            session.queue(Request(url), process_product, dict(context, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = data.xpath('//meta[@property="og:title"]/@content').string()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html')
    product.category = context['cat']
    product.manufacturer = data.xpath('//li[contains(., "Marque")]/span[@class]/text()').string()

    ean = data.xpath('//li[contains(., "EAN")]/span[@class]/text()').string()
    if ean and ean.isdigit() and len(ean) > 11:
        product.add_property(type='id.ean', value=ean)

    context['product'] = product

    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('')
#https://www.but.fr/Api/Rest/Catalog/Products/2099901391353/Reviews.json?SortedBy=DateDesc&PageSize=All