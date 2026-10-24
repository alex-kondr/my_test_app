#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.bazaarvoice_api_reviews import *
import simplejson


XCAT = ["New & Featured", "Curry", "Back to School", "Outlet", "Shoes"]


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
    session.queue(Request('https://www.underarmour.com/en-us/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ul[@id="menu"]/li')
    for cat in cats:
        url = cat.xpath('a/@href').string()
        name = cat.xpath('a//text()').string()

        if name not in XCAT and name == 'Kids':
            session.queue(Request(url), process_category, dict(cat=name))

        elif name not in XCAT:
            session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats1 = data.xpath('//details[summary[h3[contains(., "Product Category")]]]/ul/li/a')
    for cat1 in cats1:
        url = cat1.xpath('@href').string()
        cat1_name = cat1.xpath('text()').string()
        session.queue(Request(url), process_category, dict(cat=context['cat'] + '|' + cat1_name))


def process_category(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    subcats = data.xpath('//section[@id="category-list"]/ul/li/a')
    for subcat in subcats:
        url = subcat.xpath('@href').string()
        subcat_name = subcat.xpath('text()').string()
        session.queue(Request(url), process_prodlist, dict(cat=context['cat'] + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "ProductGrid_product-listing")]/div//h3/a')
    for prod in prods:
        url = prod.xpath('@href').string()
        name = prod.xpath('text()').string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))

    next_url = data.xpath('//a[@data-testid="pager-next"]/@href').string()
    if next_url and not session.seen(next_url):
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    pr = dict()
    pr['name'] = context['name']
    pr['category'] = context['cat']
    pr['url'] = context['url'].split('?')[0]
    pr['manufacturer'] = "UnderArmour"
    pr['ssid'] = data.xpath('//div[@data-bv-show="reviews"]/@data-bv-product-id').string()

    try:
        prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type": "Product"')]//text()''').string())
        pr['id.manufacturer'] = prod_json.get('mpn')
        pr['id.sku'] = prod_json.get('sku')
    except:
        pass

    passkey = 'caNcZjVkX1Gk7UMLWxnq0OlhTFyIorng8qNroUp16nHgU'
    displaycode = '2471-en_us'
    locale = 'en_CA,en_US'
    pid = pr['ssid']

    if pid and not session.seen(pid):
        process_reviews_request(data, dict(product=pr, pid=pid, passkey=passkey, locale=locale, displaycode=displaycode), session)
