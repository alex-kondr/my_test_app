from agent import *
from models.products import *
import simplejson


XCAT = ['Outlet']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.turtlebeach.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[contains(@class, "category-card-category-card")]')
    for cat in cats:
        name = cat.xpath('span/text()').string()
        url = cat.xpath('a/@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    sub_cats = data.xpath('(//div[div[text()="Platform"]])[1]//input[@type="checkbox"]')
    for sub_cat in sub_cats:
        name = sub_cat.xpath('@name').string()
        url = data.response_url + '?Platform={}'.format(name)
        session.queue(Request(url), process_prodlist, dict(cat=context['cat'] + '|' + name.split('.')[-1]))

    process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-card-details-top")]')
    for prod in prods:
        name = prod.xpath('h2/text()').string()
        url = prod.xpath('a/@href').string().split('?')[0]
        session.queue(Reuqest(url), process_product, dict(context, name=name, url=url))

    next_url = 'https://www.turtlebeach.com/api/collection-filter?handle=' + data.response_url.split('/')[-1]
    session.queue(Request(next_url), process_prodlist_next, dict(context))


def process_prodlist_next(data, context, session):
    prods = simplejson.loads(data.content).get('products', [])
    for prod in prods:
        name = prod.get('name')
        url = 'https://www.turtlebeach.com/products/' + prod.get('handle')
        session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = 'Turtle Beach'

    mpn = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if mpn:
        mpn = mpn.split('sku":"')[-1].split('","')[0]
        product.add_property(type='id.manufacturer', value=mpn)
