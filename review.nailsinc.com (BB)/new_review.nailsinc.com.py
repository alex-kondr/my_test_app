#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.yotpo_reviews import *


XCAT = ["New", "Discover", "The Nail Edit", "Outlet", "Shop by Colour", "Shop by Concern", "Bestsellers", "New In", "Online Exclusive", "Trending", 'Gift Guide']


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.nailsinc.com/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//nav[@role="navigation"]/ul/li/details')
    for cat in cats:
        name = cat.xpath('summary//text()').string(multiple=True)

        if name not in XCAT:
            cats1 = cat.xpath('.//div[@class="mega-menu__item"]')

            for cat1 in cats1:
                cat1_name = cat1.xpath('a//text()').string()
                if cat1_name not in XCAT and 'shop all' not in cat1_name.lower():
                    if cat1_name == name or ' by ' in cat1_name:
                        cat1_name = ''

                    subcats = cat1.xpath('ul/li/a')
                    for subcat in subcats:
                        subcat_name = subcat.xpath('text()').string()
                        url = subcat.xpath('@href').string()

                        if subcat_name not in XCAT and 'shop all' not in subcat_name.lower():
                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//h3[contains(@class, "pcard-title")]/a')
    for prod in prods:
        url = prod.xpath('@href').string()
        name = prod.xpath('text()').string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))

    next_url = data.xpath('//a[contains(normalize-space(span/text()), "Next")]/@href').string()
    if next_url and not session.seen(next_url):
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = dict()
    product['name'] = context['name']
    product['url'] = context['url']
    product['ssid'] = data.xpath('//product-info/@data-product-id').string()
    product['category'] = context['cat'].replace('||', '|').rstrip('|')
    product['manufacturer'] = 'Nails.INC'

    try:
        prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type":"Product"')]//text()''').string())
        product['sku'] = prod_json.get('sku')
        product['ean'] = prod_json.get('gtin')
    except:
        pass

    app_key = 'nlARHR9nOMu1xu8tQInhcGl735SG5Qi2VFqOFdb6'

    if product['ssid'] and not session.seen(product['ssid']):
        process_reviews_json_request(data, dict(context, product=product, app_key=app_key), session)
