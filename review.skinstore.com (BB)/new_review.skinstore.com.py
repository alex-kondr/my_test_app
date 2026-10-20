#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.powerreviews_api_reviews import *


XCAT = ["Discover Dermstore", "Brands", "Sale", "Blog", "Popular Categories", "Skin Care Advice", "Shop All", "Home", "Holiday Shop", "Bestsellers", "Sale & Offers", "New", "Text An Expert", "Exclusives"]
XCAT2 = ["shop all", "brands"]


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
    session.queue(Request('https://www.skinstore.com'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//nav[@aria-label="Main menu"]/div')
    for cat in cats:
        name = cat.xpath('div[contains(@class, "nav-controls")]/a//text()').string(multiple=True)

        if name and name not in XCAT:
            cats1 = cat.xpath('div[contains(@class, "navigation")]/div/div')

            for cat1 in cats1:
                cat1_name = cat1.xpath('a//text()').string(multiple=True)

                if cat1_name not in XCAT and not any(word in cat1_name.lower() for word in XCAT2):

                    if 'type' in cat1_name.lower() or 'shop by' in cat1_name.lower() or cat1_name == name:
                        cat1_name = ''

                    subcats = cat1.xpath('div/a')
                    for subcat in subcats:
                        subcat_name = subcat.xpath('text()').string()
                        url = subcat.xpath('@href').string()

                        if subcat_name not in XCAT:
                            
                            print name + '|' + cat1_name + '|' + subcat_name
                            # session.queue(Request(url), process_prodlist, dict(url=url, cat=name + '|' + cat1_name + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//li[@class="productListProducts_product "]')
    if not prods:
        return

    for prod in prods:
        url = prod.xpath('.//a[@class="productBlock_link"]/@href').string()
        name = prod.xpath('.//h3[@class="productBlock_productName"]//text()').string()
        ssid = prod.xpath('div/@data-product-id').string()
        rating = prod.xpath('.//div[@data-component="powerReviewStars"]')
        if rating:
            session.queue(Request(url), process_product, dict(context, url=url, name=name, ssid=ssid))

    next_url = data.xpath('//button[@title="Next page"]')
    if next_url:
        next_page = context.get('page', 1) + 1
        next_url = context['url'] + '?pageNumber=' + str(next_page)
        session.queue(Request(next_url), process_prodlist, dict(context, page=next_page))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = dict()
    product['name'] = context['name']
    product['url'] = context['url']
    product['category'] = context['cat'].replace('||', '|')
    product['ssid'] = context['ssid']
    product['id.ean'] = data.xpath('//div/@ data-option-barcode').string()

    try:
        prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type":"Product"')]//text()''').string())
        product['manufacturer'] = prod_json.get('brand', {}).get('name')
        product['id.manufacturer'] = prod_json.get('mpn')
    except:
        pass

    merchant_id = '678785550'
    locale = 'en_US'
    api_key = 'e8e40c10-869f-458c-981f-34877ef4fecc'

    if product['ssid'] and not session.seen(product['ssid']):
        process_reviews_request(data, dict(product=product, api_key=api_key, merchant_id=merchant_id, locale=locale), session)
