#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def Request(url):
    options = "--compressed \
    -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:158.0) Gecko/20100101 Firefox/158.0' \
    -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \
    -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' \
    -H 'Accept-Encoding: deflate' \
    -H 'Connection: keep-alive' \
    -H 'Cookie: ASP.NET_SessionId=uyir5yv41qvpvffkvhq141pc; cvf=i5LzKng08EtMDLGnlZLuxRrhb/tNlg7n/vz+S2BVfk0SEfamYbgxqjM3E+IDqlRMBIPI4kULOgoeej63gUi/b0ZfzKPtzFhf3yfWqkiXi2Y=; visitorID=AAEAAAD/////AQAAAAAAAAAGAQAAAAozODA1OTczNjV8Cw==; cp_total_cart_items=0; cp_total_cart_value=0; cpab=b6566d64-b38f-4b98-80b2-f5ca5ddf7d60; cp_sessionTime=1792428360838; cp_laternotif=yes; cookie-consent=1' \
    -H 'Upgrade-Insecure-Requests: 1' \
    -H 'Sec-Fetch-Dest: document' \
    -H 'Sec-Fetch-Mode: navigate' \
    -H 'Sec-Fetch-Site: none' \
    -H 'Priority: u=0, i' \
    -H 'Pragma: no-cache' \
    -H 'Cache-Control: no-cache' \
    -H 'TE: trailers'"
    r = agent.Request(url, use='curl', proxies=['rotating-eu', 'rotating-us'], options='-s -L --insecure '+options)
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.apothema.gr/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//ul[contains(@class, "navbar")]/li[@class="dropdown"]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        cats1 = cat.xpath('div/div[@class="col"]')
        for cat1 in cats1:
            cat1_name = cat1.xpath('h3//text()').string(multiple=True)

            subcats = cat1.xpath('ul/li/a')
            for subcat in subcats:
                subcat_name = subcat.xpath('text()').string()
                url = subcat.xpath('@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//div[contains(@class, "product__item")]/div[contains(@class, "caption")]')
    for prod in prods:
        name = prod.xpath('span/a/text()').string()
        url = prod.xpath('span/a/@href').string()

        revs_cnt = prod.xpath('.//div[@class="reviews_count"]/text()').string()
        if revs_cnt and int(revs_cnt.strip('( )')) > 0 and not session.seen(url):
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@aria-label="Next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]
    product.sku = data.xpath('//p[contains(@class, "contact-code")]/strong/text()').string()
    product.category = context['cat'].title().replace(' - ', '/')
    product.manufacturer = data.xpath('//li[contains(text(), "Κατασκευαστής:")]/a/text()').string()

    try:
        prod_json = data.xpath("""//script[contains(., '"@type": "Product"')]/text()""").string()
        prod_json = simplejson.loads(prod_json)

        mpn = prod_json.get('mpn')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)
    except:
        pass

    ean = data.xpath('//div[@data-loadbee-gtintype="ean"]/@data-loadbee-gtin').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[@id="reviews"]//div[contains(@class, "reviews__panel")]/div')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('div/p[contains(@class, "item__info")]/text()').string()
        if date:
            review.date = date.split()[-1]

        author = rev.xpath('div/p[contains(@class, "item__info")]/strong/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[contains(@class, "rating__total")]/text()').string()
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.xpath('.//h3[contains(@class, "item__title")]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[contains(@class, "item__text")]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
