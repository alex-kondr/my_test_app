#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.yotpo_reviews import *
import simplejson

XCAT = ['Nail Colors', 'OPI Guides']


import agent
def request(url, formdata=False):
    additional_headers =  ' -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8" '
    additional_headers += ' -H "User-Agent: Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36" '

    if not formdata:
        r = agent.Request(url, max_age=0, use="curl", options='-s -L --insecure ' + additional_headers, proxies=proxy_list[:])
    else:
        additional_headers += ' -H "Content-Type: application/json" '
        r = agent.Request(url, ignore_errors=True, max_age=0, use="curl", options="-s -L --insecure -X POST" + additional_headers + "-d '" + formdata +"'")

    return r
RequestX = request


def run(context, session): 
    session.queue(Request('https://www.opi.com/'), process_frontpage, dict(context))
    session.queue(Request('https://www.opi.com/en-GB'), process_frontpage, dict(gb=True))


def process_frontpage(data, context, session):
    for cat in data.xpath('//div[contains(@class,"menu-item__professionals") or contains(@class,"menu-item__products")]//li//a'):
        category = cat.xpath("descendant::text()").string()
        cat_url = cat.xpath("@href").string()
        if category in XCAT: continue
        if category and cat_url:
            context['category'] = category
            session.queue(Request(cat_url), process_category_JSON, dict(context))


def process_category_JSON(data, context, session):
    json_data = data.xpath('//script[@id="__NEXT_DATA__"]/text()').string()
    if json_data:
        if ',"translation"' in json_data: json_data = json_data.split(',"translation"')[0] + '}'
        json_data = '{"algoliaServerState"' + json_data.split('"algoliaServerState"')[1]
        #print json_data
        cats = yaml.load(json_data)
        lang = 'en-US'
        if context.get('gb'): lang = 'en-GB'
        pages = cats['algoliaServerState']['initial']['initialResults'][lang + '--shopify_products']['results'][0]['nbPages']
        filters = cats['algoliaServerState']['initial']['initialResults'][lang + '--shopify_products']['results'][0]['params'].replace('&distinct=true','')

        req_url = 'https://0p2oop9zoz-dsn.algolia.net/1/indexes/*/queries?x-algolia-agent=Algolia%20for%20JavaScript%20(4.14.3)%3B%20Browser%20(lite)%3B%20instantsearch.js%20(4.53.0)%3B%20react%20(18.2.0)%3B%20react-instantsearch%20(6.38.1)%3B%20react-instantsearch-hooks%20(6.38.1)%3B%20JS%20Helper%20(3.12.0)&x-algolia-api-key=1986f53b4416185d50aee77c7f004dfe&x-algolia-application-id=0P2OOP9ZOZ'

        for x in xrange(0, pages+1):
            req_json = '{"requests":[{"indexName":"' + lang + '--shopify_products","params":"distinct=true&facets=%5B%22meta.wmw.color_collection%22%2C%22meta.opi.primary_color_family%22%2C%22meta.opi.finish%22%2C%22product_type%22%5D&' + filters + '%20AND%20NOT%20tags%3APro&maxValuesPerFacet=18&page=' + str(x) + '&ruleContexts=%5B%22collection-page%22%5D&tagFilters="}]}'
            session.queue(RequestX(req_url, req_json), process_productlist_JSON, dict(context))


def process_productlist_JSON(data, context, session):
    prods = simplejson.loads(data.content)
    for prod in prods['results'][0]['hits']:
        name = prod['title']
        url = 'https://www.opi.com/products/' + prod['handle']
        if context.get('gb'):  url = 'https://www.opi.com/en-GB/products/' + prod['handle']
        ssid = str(prod['id'])
        sku = str(prod['sku'])
        rated = prod['meta'].get('yotpo')
        if name and ssid and rated and not(session.seen(ssid)):
            if rated.get('reviews_count') > 0:
                session.queue(Request(url), process_product, dict(context, name=name, ssid=ssid, url=url, sku=sku))


def process_product(data, context, session):
    product = dict()
    product['name'] = context['name']
    product['ssid'] = context['ssid']
    product['sku'] = context['sku']
    product['url'] = context['url']
    product['category'] = context['category']
    product['manufacturer'] = 'OPI'

    app_key = 'PhLkfX6lTHIVJEeMLLDNXL9kuSOZnCYnzF9LMp6j'
    if 'en-GB' in product['url']: app_key = 'j7Ghzfv6y8jr3QLTFxwTsgyygCl76Wxn0q7jZEqg'
    process_reviews_json_request(data, dict(context, product=product, app_key=app_key), session)
