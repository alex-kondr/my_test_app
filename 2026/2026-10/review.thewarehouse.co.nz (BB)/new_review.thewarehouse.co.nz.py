#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.bazaarvoice_api_reviews import *


XCAT = ['Labour Weekend Deals', 'Halloween', 'New & Trending', 'Marketplace', 'Gifting', 'Christmas', 'New Arrivals', 'Clearance', 'Top Brands', 'New Releases', 'Giant Tech Sale', "Father's Day", "Specials", "Official Merchandise"]
XCAT2 = ['top', 'gift', 'shop by', 'clearance', 'featured', 'service', 'explore']


def Request(url):
    r = agent.Request(url, use='curl', proxies=['rotating-us'], force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.thewarehouse.co.nz/home'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//ul[contains(@class, "mega-menu-root")]/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_category, dict(url=url, cat=name))


def process_category(data: Response, context: dict[str, str], session: Session):
    subcats = data.xpath('//li[a[contains(@class, "btn selected")]]/ul/li/a')
    if not subcats:
        process_prodlist(data: Response, context: dict[str, str], session: Session)
        return

    for subcat in subcats:
        subcat_name = subcat.xpath('text()').string(multiple=True).replace('Other ', '')
        url = subcat.xpath('@href').string()

        if subcat_name == context['cat'].split('|')[-1]:
            subcat_name = ''

        if not any(word in subcat_name.lower() for word in XCAT2) and subcat_name not in XCAT:
            session.queue(Request(url), process_category, dict(url=url, cat=context['cat'] + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//div[@data-pid]')
    for prod in prods:
        pr = dict()
        pr['name'] = prod.xpath('a[contains(@class, "link")]//text()').string()
        pr['url'] = prod.xpath('a[contains(@class, "link")]/@href').string()
        pr['ssid'] = prod.xpath('@data-pid').string()
        pr['id.sku'] = pr['ssid']
        pr['category'] = context['cat'].replace('||', '|').rstrip('|')

        try:
            prod_json = simplejson.loads(prod.xpath('@data-gtm-product').string())

            manufacturer = prod_json.get('brand')
            if manufacturer != "na":
                pr['manufacturer'] = manufacturer

            ean = prod_json.get('productEAN')
            if ean and ean.isdigit():
                pr['id.ean'] = ean
        except:
            pass

        rating = prod.xpath('.//div[@class="ratings"]/div/span/text()')
        if rating:
            passkey = 'cayrDXE7GFTzWCbACNE3sAwgn6jk6hE16qaeQdQklo8k4'
            displaycode = '14837-en_nz'
            locale = 'en*,en_NZ'
            pid = pr['ssid']

            if pid and not session.seen(pid):
                process_reviews_request(data, dict(product=pr, pid=pid, passkey=passkey, locale=locale, displaycode=displaycode), session)

    next_url = data.xpath('//gep-search-pagination/@next-url').string()
    if next_url:
        next_url = 'https://www.thewarehouse.co.nz' + next_url
        if not session.seen(next_url):
            session.queue(Request(next_url), process_prodlist, dict(context))
