from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.cyberphoto.se/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats_json = data.xpath('//json-data/text()').string()
    if cats_json:
        cats = simplejson.loads(cats_json).get('mobileContentLinks', [{}])[0].get('links', [])

        for cat in cats:
            name = cat.get('name')

            sub_cats = cat.get('links', [])
            for sub_cat in sub_cats:
                sub_name = sub_cat.get('name')
                url = sub_cat.get('url')
                session.queue(Request('https://www.cyberphoto.se' + url), process_prodlist, dict(cat='Foto & Video|' + name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "overflow-y-hidden")]')
    for prod in prods:
        name = prod.xpath('a/text()').string()
        manufacturer = prod.xpath('div[contains(@class, "text-sm")]/text()').string()
        url = prod.xpath('a/@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, manufacturer=manufacturer, url=url))

    next_url = data.xpaht('//a[contains(., "Ladda fler")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
