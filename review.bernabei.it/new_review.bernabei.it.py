from agent import *
from models.products import *
import simplejson


XCAT = ['Offerte', 'Esperienze']


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.bernabei.it'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "level0")]/a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    sub_cats = data.xpath('//dd[@class="champagne_tipologia"]//li/a')
    if not sub_cats:
        sub_cats = data.xpath('//dd[@class="tipologia"]//li/a')
    if not sub_cats:
        process_prodlist(data, context, session)

    for sub_cat in sub_cats:
        sub_name = sub_cat.xpath('text()').string().strip('()')
        url = sub_cat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=context['cat'] + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="item-title"]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@class="button next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="product"]/@value').string()
    product.sku = product.ssid

    prod_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.sku = prod_json.get('sku')
