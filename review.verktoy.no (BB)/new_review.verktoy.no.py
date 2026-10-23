#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.trustpilot_reviews import *


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
    url = url.replace("www.verkt%C3%B8y.no", "www.xn--verkty-fya.no")
    url = url.replace("www.verktøy.no", "www.xn--verkty-fya.no")
    r = agent.Request(url, force_charset='utf-8', proxies=['rotating-us', 'rotating-eu'])
    return r


def RequestProds(cat, subcat, offset):
    url = 'https://prod-retail-proxy-857687180900.europe-north2.run.app/?action=search&config=default_search'
    payload = {
        "pageSize": 24,
        "offset": offset,
        "visitorId": "90511362.701503470",
        "filter": "attributes.category_level1: ANY(\"{cat}\") AND attributes.category_level2: ANY(\"{subcat}\")".format(cat=cat.upper(), subcat=subcat),
        "languageCode": "no-NO",
        "entity": "verktoy",
        "queryExpansionSpec": {
            "condition": "AUTO"
        }
    }
    payload = simplejson.dumps(payload, separators=(",", ":"))
    options = """--compressed \
        -X POST \
        -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:158.0) Gecko/20100101 Firefox/158.0' \
        -H 'Accept-Encoding: deflate' \
        -H 'Content-Type: application/json' \
        -H 'X-HTTP-KEY: fe2f6c75e24b464f4184c4885990eb6360def6b3'"""
    options += " --data '" + payload + "'"
    r = agent.Request(url, use='curl', force_charset='utf-8', options='-s -L --insecure '+options, proxies=['rotating-us', 'rotating-eu'])
    return r


def RequestCats():
    graphql_query = """query($id: String!, $parentId: Int) {
        navigationMenu(identifier: $id, parentId: $parentId) {
            items {
                node_id parent_id level type title url image image_alt_text classes position has_children
            }
        }
    }"""

    payload_dict = {
        "query": graphql_query,
        "variables": {"id": "hyva-topmenu-mobile", "parentId": 130},
    }

    payload = simplejson.dumps(payload_dict, separators=(",", ":"))
    options = (
        "--compressed -X POST "
        "-H 'User-Agent: Mozilla/5.0 (Android 15; Mobile; rv:145.0.2) Gecko/145.0.2 Firefox/145.0.2' "
        "-H 'Content-Type: application/json' "
    )

    options += " --data '" + payload + "'"
    url = "https://www.xn--verkty-fya.no/graphql"
    r = agent.Request(url, force_charset='utf-8', options='-s -L --insecure '+options, use='curl', proxies=['rotating-us', 'rotating-eu'])
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(RequestCats(), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    try:
        cats = simplejson.loads(data.content).get('data', {}).get('navigationMenu', {}).get('items', [])
    except:
        return

    sorted_cats = {}
    for cat in cats:
        if cat.get('level') == 1:
            if sorted_cats.get(cat['node_id']):
                sorted_cats[cat['node_id']]['title'] = cat['title']
            else:
                sorted_cats[cat['node_id']] = dict(title=cat['title'], subcats=[])
        elif cat.get('level') == 2:
            if sorted_cats.get(cat['parent_id']):
                sorted_cats[cat['parent_id']]['subcats'].append(dict(title=cat['title']))
            else:
                sorted_cats[cat['parent_id']] = dict(subcats=[dict(title=cat['title'])])

    for cat in sorted_cats.values():
        name = cat['title']

        subcats = cat['subcats']
        for subcat in subcats:
            subcat_name = subcat['title']
            session.queue(RequestProds(name, subcat_name, 0), process_prodlist, dict(cat=name, subcat=subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    try:
        prods_json = simplejson.loads(data.content)
    except:
        prods_json = {}

    prods = prods_json.get('results', [])
    for prod in prods:
        pr = dict()
        pr['name'] = prod.get('product', {}).get('title')
        pr['url'] = prod.get('product', {}).get('uri')
        pr['sku'] = prod.get('id')
        pr['category'] = context['cat'] + '|' + context['subcat']
        pr['manufacturer'] = prod.get('product', {}).get('brands', [''])[0]

        if not session.seen(pr['sku']):
            session.queue(Request(pr['url']), process_product, dict(product=pr))

    prods_cnt = context.get('prods_cnt', prods_json.get('totalSize', 0))
    offset = context.get('offset', 0) + 24
    if prods_cnt and int(prods_cnt) > offset:
        session.queue(RequestProds(context['cat'], context['subcat'], offset), process_prodlist, dict(context, offset=offset, prods_cnt=prods_cnt))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    context['product']['ssid'] = data.xpath('//td[@data-th="UNSPSC"]//text()').string()
    context['product']['mpn'] = data.xpath('//div[contains(span, "Supplier number")]/span[contains(@class, "product-detail-value")]/text()').string()
    context['product']['ean'] = data.xpath('//td[@data-th="EAN/GTIN"]//text()').string()

    trustpilot = data.xpath('//div[@id="trustpilot-reviews"]/div[@class="trustpilot-widget"]').first()
    if trustpilot:
        app_key = trustpilot.xpath("@data-template-id").string()
        businessunit = trustpilot.xpath("@data-businessunit-id").string()
        locale = trustpilot.xpath("@data-locale").string()

        process_reviews_json_request_TP(data, dict(context, app_key=app_key, businessunit=businessunit, locale=locale), session)
