#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.bazaarvoice_api_reviews import *
import simplejson


XCAT = ['Sale']


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


def Request(url):
    r = agent.Request(url, use='curl', proxies=['rotating-us'], force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request("https://www.thule.com/en-us/"), process_cats_json, dict())


def process_cats_json(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats_json = data.xpath('''//script[contains(., '"ProductSections":')]//text()''').string()
    if not cats_json:
        print('CATS JSON CHANGED')
        return

    cats = simplejson.loads(cats_json.split('"ProductSections":')[1].split('"Title":"Shop by product"')[0].rstrip(', '))
    for cat in cats:
        name = cat['Name']
        if name not in XCAT:
            cats1 = cat['Categories']
            for cat1 in cats1:
                cat1_name = cat1['Name']
                url = 'https://www.thule.com' + cat1['Link']
                subcats = cat1.get('SubCategories')
                if subcats:
                    for subcat in subcats:
                        subcat_name = subcat['Name']
                        url = 'https://www.thule.com' + subcat['Link']
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name))
                else:
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//article[@class="product-list-item "]')
    for prod in prods:
        url = prod.xpath('.//a[@itemprop="item"]/@href').string()
        name = prod.xpath('.//h2[@itemprop="name"]//text()').string()
        sku = prod.xpath('@data-productid').string()
        if sku and not session.seen(sku):
            session.queue(Request(url), process_product, dict(context, url=url, name=name, sku=sku))


def process_product(data: Response, context: dict[str, str], session: Session):
    pr = dict()
    pr['name'] = context['name']
    pr['category'] = context['cat']
    pr['url'] = context['url']
    pr['id.sku'] = context['sku']
    pr['ssid'] = pr['id.sku']

    try:
        prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type": "Product"')]//text()''').string())
        pr['manufacturer'] = prod_json.get('brand', {}).get('name')
        pr['id.ean'] = prod_json.get('gtin12')
    except:
        pass

    passkey = 'calKvzGlyCAQkrbHYVfyaYgFi9SMWiI7oU5wOKy5r803c'
    displaycode = '18088_1_0-en_us'
    locale = 'en*,en_US'
    pid = pr['ssid']

    process_reviews_request(data, dict(product=pr, pid=pid, passkey=passkey, locale=locale, displaycode=displaycode), session)
