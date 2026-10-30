#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.bazaarvoice_api_reviews import *


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

    try:
        cats_json = data.xpath('''//script[contains(., '"ProductSections":')]//text()''').string()
        cats = simplejson.loads(cats_json.split('"ProductSections":', 1)[-1].split('"Title":"Shop by product"')[0].rstrip(', '))
    except:
        return

    for cat in cats:
        name = cat['Name']

        if name not in XCAT:
            cats1 = cat.get('Categories', [])
            for cat1 in cats1:
                cat1_name = cat1.get('Name')

                subcats = cat1.get('SubCategories', [])
                if subcats:
                    for subcat in subcats:
                        subcat_name = subcat.get('Name')
                        url = 'https://www.thule.com' + subcat.get('Link')
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name))
                else:
                    url = 'https://www.thule.com' + cat1.get('Link')
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//article[contains(@data-producttype, "Main product")]')
    for prod in prods:
        url = prod.xpath('.//a[contains(@class, "product-link")]/@href').string()
        name = prod.xpath('.//h2[contains(@class, "product-item-name")]//text()').string()
        ssid = prod.xpath('@data-productid').string()

        if ssid and not session.seen(ssid):
            session.queue(Request(url), process_product, dict(context, url=url, name=name, ssid=ssid))


def process_product(data: Response, context: dict[str, str], session: Session):
    pr = dict()
    pr['name'] = context['name']
    pr['url'] = context['url']
    pr['ssid'] = context['ssid']
    pr['id.sku'] = pr['ssid']
    pr['category'] = context['cat']
    pr['id.ean'] = data.xpath('//div[contains(p/text(), "UPC-A")]/p/span/text()').string()

    try:
        prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type": "Product"')]//text()''').string())
        pr['manufacturer'] = prod_json.get('brand', {}).get('name')
    except:
        pass

    passkey = 'calKvzGlyCAQkrbHYVfyaYgFi9SMWiI7oU5wOKy5r803c'
    displaycode = '18088_1_0-en_us'
    locale = 'en*,en_US'
    pid = pr['ssid']

    process_reviews_request(data, dict(product=pr, pid=pid, passkey=passkey, locale=locale, displaycode=displaycode), session)
