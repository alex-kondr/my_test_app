#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.bazaarvoice_api_reviews import *


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
    options = "--compressed -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/112.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br' -H 'Connection: keep-alive' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: cross-site' -H 'TE: trailers'"
    r = agent.Request(url, force_charset='utf-8', use='curl', options='-s -L --insecure '+options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.elcorteingles.es/hp/'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//li[@class="filters-item _hierarchy _unset"]//ol[@class="filters-values"]/li/a')
    for cat in cats:
        name =  context.get('cat', '') + "|" + cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_catlist, dict(cat=name))
    
    if not cats:
        process_prodlist(data: Response, context: dict[str, str], session: Session)


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//li[@class="products_list-item"]')
    for prod in prods:
        name = prod.xpath('.//a[contains(@class, "product_preview-title")]//text()').string()
        url = prod.xpath('.//a[contains(@class, "product_preview-title")]/@href').string() + "&bm-verify=AAQAAAAH_____7MkUX0weR88Dnbe_xpk89v-2dnIx_e_l1eTrl0lLTYpz6nWFtl8BehZIZAgn2sdUHGJ12M_6CFelbzkI3pSqWtjbsG69Oz3NJYmvczsdzxnmljlA-R-8eUQ_ra_teoSOEMPPRF7Iy4PP9hE0VK0sUd4ln05oS92QQiXo5heeGqmkcR3vK7jq2yVzqq2vJxqXZ4t75BQz7EZisycSS5TykwzPwxDlpVl947vDEiXFFke50mjVopPAJZ2jFWp4luWdyIddBgsgIohwQ2ghgV6i-S0_SFZShz-OOTVfNfctMGzdnSDRinJS9pfDmj4HN8ihxhfs-LqAFKN-rLEVlcuElC6edpw43679GlM0K3907N4ICUWPjWldYSMQhThLr84ytzjtT5yExAMJc29Af6LaYSoHsFTj53pa6EzDw4"
        brand = prod.xpath('.//div[@class="product_preview-brand"]//text()').string()
        ssid = prod.xpath('@data-product-id').string()
        
        if not session.seen(ssid):
            session.queue(Request(url), process_product, dict(context, brand=brand, name=name, url=url, ssid=ssid))
    
    next_url = data.xpath('//li[@id="pagination-next"]/a/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = dict()
    product['name'] = context['name']
    product['url'] = context['url'].split('?parentCategory')[0]
    product['manufacturer'] = context['brand']
    product['category'] = context['cat'].lstrip('|')

    product['id.sku'] = data.xpath("//input/@data-flix-sku").string()
    product['id.manufacturer'] = data.xpath("//input/@data-flix-mpn").string()
    product['id.ean'] = data.xpath("//input/@data-flix-ean").string()
    product['ssid'] = context['ssid']

    passkey = 'caBFucP0zZYZzTkaZEBiCUIK6sp46Iw7JWooFww0puAxQ'
    locale = 'es_ES'
    displaycode = '4572-es_es'

    process_reviews_request(data, dict(product=product, pid=product['ssid'], passkey=passkey, locale=locale, displaycode=displaycode), session)
