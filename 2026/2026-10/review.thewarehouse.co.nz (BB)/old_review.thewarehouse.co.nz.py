#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.bazaarvoice_api_reviews import *


XCAT = ['Labour Weekend Deals', 'Halloween', 'New & Trending', 'Marketplace', 'Gifting', 'Christmas', 'New Arrivals', 'Clearance', 'Top Brands', 'New Releases', 'Giant Tech Sale', "Father's Day", "Specials", "Official Merchandise"]
XCAT2 = ['top', 'gift', 'shop by', 'clearance', 'featured', 'service', 'explore']


def Request(url):
    r = agent.Request(url, use='curl', proxies=['rotating-us'])
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.thewarehouse.co.nz/home'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//ul[@class="mega-menu-root-list"]/li/a')
    for cat in cats:
        url = cat.xpath('@href').string()
        name = cat.xpath('text()').string()
        if name not in XCAT:
            session.queue(Request(url), process_category, dict(url=url, cat=name))


def process_category(data: Response, context: dict[str, str], session: Session):
    subcats = data.xpath('//li[a[contains(@class, "selected")]]/ul/li/a')
    if not subcats:
        process_prodlist(data: Response, context: dict[str, str], session: Session)
        return

    for subcat in subcats:
        url = subcat.xpath('@href').string()
        subcat_name = subcat.xpath('text()').string(multiple=True).replace('Other ', '')

        if subcat_name == context['cat'].split('|')[-1]:
            subcat_name = ''

        if not any(word in subcat_name.lower() for word in XCAT2) and subcat_name not in XCAT:
            session.queue(Request(url), process_category, dict(url=url, cat=context['cat'] + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//div[@data-ga-product]')
    for prod in prods:
        pr = dict()
        pr['name'] = prod.xpath('a[contains(@class, "link")]//text()').string()
        pr['category'] = context['cat'].replace('||', '|').rstrip('|')
        pr['url'] = prod.xpath('a[contains(@class, "link")]/@href').string()

        pr['id.sku'] = prod.xpath('@data-pid').string()
        pr['ssid'] = pr['id.sku']

        try:
            prod_json = simplejson.loads(prod.xpath('@data-gtm-product').string())

            manufacturer = prod_json.get('brand')
            if manufacturer != "na":
                pr['manufacturer'] = manufacturer

            ean = prod_json.get('productEAN')
            if ean and ean.isdigit() == True:
                pr['id.ean'] = ean

        except:
            pass

        rating = prod.xpath('.//div[contains(@class, "rating rating")]')
        if rating:
            passkey = 'cayrDXE7GFTzWCbACNE3sAwgn6jk6hE16qaeQdQklo8k4'
            displaycode = '14837-en_nz'
            locale = 'en*,en_NZ'
            pid = pr['ssid']

            if pid and not session.seen(pid):
                process_reviews_request(data, dict(product=pr, pid=pid, passkey=passkey, locale=locale, displaycode=displaycode), session)

    prods_cnt = context.get('prods_cnt', data.xpath('//div[@class="result-count"]/p//text()').string())
    offset = context.get('offset', 0) + 32
    next_link = data.xpath('//gep-search-pagination/@next-url').string()
    if next_link and prods_cnt and int(prods_cnt.split(' of ')[-1].split()[0].replace(',', '')) > offset:
        next_url = 'https://www.thewarehouse.co.nz' + next_link
        if not session.seen(next_url):
            session.queue(Request(next_url), process_prodlist, dict(context, prods_cnt=prods_cnt, offset=offset))
