#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.yotpo_reviews import *


def Request(url):
    r = agent.Request(url, use='curl', force_charset='utf-8')
    return r


def RequestJson(page):
    url = "https://api.fastsimon.com/categories_navigation?request_source=v-next&src=v-next&UUID=b9bb47fa-0aed-4b9b-b962-27ef65b41723&uuid=b9bb47fa-0aed-4b9b-b962-27ef65b41723&store_id=1&api_type=json&category_id=10&facets_required=1&products_per_page=15&page_num=" + str(page) + "&with_product_attributes=true"
    options = "--compressed -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0' -H 'Accept: application/json, text/plain, */*' -H 'Accept-Language: en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br'"
    r = agent.Request(url, use='curl', force_charset='utf-8', options='-s -L --insecure '+options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    # https://www.precision-camera.com/photo/
    session.queue(RequestJson(1), process_prodlist, dict(cat='Digital Cameras'))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods_json = simplejson.loads(data.content)

    prods = prods_json.get('items', [])
    for prod in prods:
        name = prod['l']
        url = "https://www.precision-camera.com" + prod['u']
        ssid = prod['id']
        session.queue(Request(url), process_product, dict(context, name=name, url=url, ssid=ssid))

    prods_cnt = context.get('prods_cnt', prods_json.get('total_results'))
    offset = context.get('offset', 0) + 15
    if prods_cnt and int(prods_cnt) > offset:
        next_page = context.get('page', 1) + 1
        session.queue(RequestJson(next_page), process_prodlist, dict(context, offset=offset, page=next_page))


def process_product(data: Response, context: dict[str, str], session: Session):
    prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type": "Product"')]//text()''').string())

    product = dict()
    product['name'] = context['name']
    product['url'] = context['url']
    product['category'] = context['cat']
    product['ssid'] = context['ssid']
    product['manufacturer'] = prod_json.get('brand', {}).get('name', data.xpath('//p[@class="card-text card-brand"]//text()').string())
    product['ean'] = prod_json.get('gtin11')

    mpn = prod_json.get('mpn', context.get('mpn'))
    if mpn and mpn.isdigit() == True and len(mpn) > 10 and not product['ean']:
        product['ean'] = mpn
    elif mpn:
        product['sku'] = mpn

    app_key = "HTPA0QFbpJz70Is8NW67fhEEpsWmGldE0K0aklrR"

    process_reviews_json_request(data, dict(context, product=product, app_key=app_key), session)
