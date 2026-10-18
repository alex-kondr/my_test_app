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
    session.queue(Request('https://www.elcorteingles.es/hp/'), process_prodlist, dict())


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//article[contains(@class, "product_preview")]')
    for prod in prods:
        name = prod.xpath('.//div[contains(@class, "title")]//h2/a/text()').string()
        url = prod.xpath('.//div[contains(@class, "title")]//h2/a/@href').string()
        ssid = prod.xpath('@id').string()

        if not session.seen(ssid):
            session.queue(Request(url), process_product, dict(context, name=name, url=url, ssid=ssid))

    prods_cnt = context.get('prods_cnt', data.xpath('//span[contains(@class, "title_h1__total-text")]/text()').string())
    offset = context.get('offset', 0) + 12
    if offset < int(prods_cnt.split()[0].strip('( )')):
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.elcorteingles.es/hp/{}/'.format(next_page)
        session.queue(Request(next_url), process_prodlist, dict(context, offset=offset, page=next_page, prods_cnt=prods_cnt))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = dict()
    product['name'] = context['name']
    product['url'] = context['url']
    product['ssid'] = context['ssid']
    product['category'] = data.xpath('//li[contains(@class, "breadcrumb__item")]//text()').join('|')
    product['manufacturer'] = data.xpath('//a[@itemprop="brand"]/text()').string()

    sku = data.xpath('//div[contains(text(), "Referencia:")]/text()').string()
    if sku:
        product['id.sku'] = sku.replace('Referencia:', '').strip()

    mpn = data.xpath('//div[contains(text(), "Modelo:")]/text()').string()
    if mpn:
        product['id.manufacturer'] = mpn.replace('Modelo:', '').strip()

    ean = data.xpath('//div[contains(text(), "EAN:")]/text()').string()
    if ean:
        product['id.ean'] = ean.replace('EAN:', '').strip()

    passkey = 'caBFucP0zZYZzTkaZEBiCUIK6sp46Iw7JWooFww0puAxQ'
    locale = 'es_ES'
    displaycode = '4572-es_es'

    process_reviews_request(data, dict(product=product, pid=product['ssid'], passkey=passkey, locale=locale, displaycode=displaycode), session)
