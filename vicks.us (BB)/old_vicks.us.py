#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.bazaarvoice_api_reviews import *


XCAT = ["BY COLLECTION", "BY NEED", "ALL TIME FAVORITE"]


def Request(url):
    r = agent.Request(url, force_charset='utf-8')
    return r


def RequestProds(cat_id):
    url = "https://dmj3e8mfx7-dsn.algolia.net/1/indexes/prod_HS_IN_Product_en-us_asc(title)/query?x-algolia-agent=Algolia%20for%20JavaScript%20(4.24.0)%3B%20Browser"
    options = """--compressed -X POST -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0' -H 'Accept: */*' -H 'Accept-Language: en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'x-algolia-api-key: 376bac226edc4e2d7b0c2d29511103dd' -H 'x-algolia-application-id: DMJ3E8MFX7' -H 'content-type: application/x-www-form-urlencoded' --data-raw '{"query":"","facets":["cold_flu","cough","sinus_nasal_congestion","sore_throat","chest_congestion","soothing","immune_support","drug_free","high_blood_pressure","flu_therapy","adult","child","twotosix","baby","threetotwelve","liquids","liquidcaps_caplets","rubs","nasal_spray_saline","drops_lozenges","soothing_vapors","throat_spray","chewable_tablet_gummies","hot_drink_mix","non_drowsy","day_night","alcohol_free","sugar_free","gluten_free","lactose_free","dye_free","scented_flavoured"],"facetFilters":[["facetCollection.form: """ + cat_id + """"],[]],"hitsPerPage":100}'"""
    r = agent.Request(url, use='curl', force_charset='utf-8', options='-s -L --insecure '+options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://vicks.com/en-us'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    cats_json = simplejson.loads(data.xpath('//script[@id="__NEXT_DATA__"]//text()').string())

    cats = cats_json.get('props', {}).get('pageProps', {}).get('header', {}).get('data', {}).get('headerCollection', {}).get('items', [{}])[0].get('primaryNavCollection', {}).get('items', [{}])[0].get('menuItemsCollection', {}).get('items', [])
    for cat in cats:
        name = cat.get('title')

        if name not in XCAT:
            subcats = cat.get('menuItemsCollection', {}).get('items', [])

            for subcat in subcats:
                subcat_name = subcat.get('name')
                url = subcat.get('link', {}).get('url', '')

                if subcat_name and url:
                    url = "https://vicks.com/en-us/" + url
                    session.queue(Request(url), process_cat_id, dict(cat=subcat_name.strip(), url=url))


def process_cat_id(data: Response, context: dict[str, str], session: Session):
    cat_id = data.xpath('''//script[contains(., '","facetCategory":')]//text()''').string()
    if cat_id:
        cat_id = cat_id.split('","facetCategory":')[0].split('":"')[-1]
    else:
        cat_id = context['url'].split(':')[-1]

    session.queue(RequestProds(cat_id), process_prodlist, dict(context))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods_json = simplejson.loads(data.content)

    prods = prods_json.get('hits', [])
    for prod in prods:
        pr = dict()
        pr['name'] = prod.get('title')
        pr['url'] = "https://vicks.com" + prod.get('url', '')
        pr['ssid'] = prod.get('ratingAndReviewId')
        pr['category'] = context['cat']
        pr['manufacturer'] = 'Vicks'

        pr['id.ean'] = prod.get('gtin')

        revs_cnt = prod.get('total_review_count')
        if revs_cnt and int(revs_cnt) > 0:
            passkey = 'caQMSYkNMXhrIQGC9ReEXLk1jUwK4xMxzFwYJY80uZxqc'
            displaycode = ''
            locale = 'en_US'
            pid = pr['ssid']

            if pid and not session.seen(pid):
                process_reviews_request(data, dict(product=pr, apiversion=5.4, pid=pid, passkey=passkey, locale=locale, displaycode=displaycode), session)
