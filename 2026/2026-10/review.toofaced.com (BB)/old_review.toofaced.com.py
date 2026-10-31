#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.powerreviews_api_reviews import *


XCAT = ['Cyber Monday', 'Holiday Gifts', 'Bestsellers', 'New', 'Trends', 'Travel Size', 'Services', 'By Collection', 'More Fun', 'Gifts & Sets', 'Offers']


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        line = line.encode('unicode_escape')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def Request(url):
    options = "--compressed -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br' -H 'Connection: keep-alive' -H 'Upgrade-Insecure-Requests: 1'"
    r = agent.Request(url, use='curl', options='-s -L --insecure '+options, max_age=0, force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.toofaced.com/'), process_frontpage, context)


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="site-header__menu-list"]/div')
    for cat in cats:
        name = cat.xpath('div/a/span//text()').string()

        if name and name not in XCAT:
            cats1 = cat.xpath('.//div[contains(@class, "menu__item--category")]')

            for cat1 in cats1:
                cat1_name = cat1.xpath('div[contains(@class, "gnav-section__link-wrapper")]/a//text()').string()

                if cat1_name and cat1_name not in XCAT:
                    subcats = cat1.xpath('.//a[contains(@class, "sub-category-link")]')

                    for subcat in subcats:
                        url = subcat.xpath('@href').string()
                        subcat_name = subcat.xpath('text()').string()

                        if subcat_name and subcat_name not in XCAT:
                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[@class=" product-grid__content "]/div')
    for prod in prods:
        url = prod.xpath('.//a[contains(@class, "product-link")]/@href').string()
        name = prod.xpath('.//div[@class="product-brief__name"]/span//text()').string()
        ssid = prod.xpath('@data-product-id').string()
        revs_cnt = prod.xpath('.//div[contains(@class, "review-count")]//text()').string()
        if ssid:
            session.queue(Request(url), process_product, dict(context, url=url, name=name, ssid=ssid))

    # no next page


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = dict()
    product['name'] = context['name']
    product['url'] = context['url']
    product['category'] = context['cat'].replace('By Category|', '')
    product['ssid'] = context['ssid'].replace('PROD', '')
    product['manufacturer'] = "Too Faced"

    ean = data.xpath('''//script[contains(., '"UPC_CODE":"')]//text()''').string()
    if ean:
        ean = ean.split('"UPC_CODE":"')[-1].split('"')[0]
        if ean and ean.isdigit() == True and len(ean) > 11:
            product['id.ean'] = ean

    mpn = data.xpath('''//script[contains(., '"PRODUCT_CODE":"')]//text()''').string()
    if mpn:
        mpn = mpn.split('"PRODUCT_CODE":"')[-1].split('"')[0]
        if mpn:
            product['id.manufacturer'] = mpn

    merchant_id = '398634'
    locale = 'en_US'
    api_key = 'b5d1f926-221a-4eed-b2b6-1935e6aa804c'

    if not session.seen(product['ssid']):
        process_reviews_request(data, dict(product=product, api_key=api_key, merchant_id=merchant_id, locale=locale), session)
