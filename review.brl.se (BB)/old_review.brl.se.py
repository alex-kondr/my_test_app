#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from datetime import datetime
import simplejson


XCAT = ['Paketlösningar', 'Nyheter']


def Request(url):
    r = agent.Request(url, force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.brl.se'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//li[@class="topKateg"]')
    for cat in cats:
        name = cat.xpath("a//text()").string()

        if name not in XCAT:
            cats1 = cat.xpath('.//li[@class="Kateg"]')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a//text()').string()
                url = cat1.xpath('@href').string()

                subcats = cat1.xpath('.//li[@class="undrKateg"]/a')
                if subcats:
                    for subcat in subcats:
                        subcat_name = subcat.xpath('text()').string()
                        url = subcat.xpath('@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name + "|" + cat1_name + "|" + subcat_name))
                else:
                    session.queue(Request(url), process_prodlist, dict(cat=name + "|" + cat1_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//div[contains(@class, "gutter-md-B gutter-md-T")]/div')
    for prod in prods:
        name = prod.xpath('.//div[@class="PT_Faktaruta"]/div//text()').string()
        url = prod.xpath('.//div[@class="PT_Faktaruta"]/a/@href').string()

        revs_cnt = prod.xpath('.//div[@class="medelbetyg ttmall"]//text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(., "Nästa")]/@href').string()
    if next_url and not session.seen(next_url):
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.ssid = product.url.split('/')[-1].replace('.html', '')

    if session.seen(product.ssid):
        return

    prod_json = data.xpath('''//script[contains(text(), '"@type": "Product"')]//text()''').string()
    if not prod_json:
        return

    prod_json = simplejson.loads(prod_json)

    product.manufacturer = prod_json.get('brand', {}).get('name')

    mpn = prod_json.get('sku')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = prod_json.get('gtin8')
    if ean:
        product.add_property(type='id.ean', value=str(ean))

    revs = prod_json.get('review', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('datePublished')
        if date:
            review.date = datetime.strptime(date, "%Y%m%d").strftime('%d.%m.%Y')

        author = rev.get('author', {}).get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('reviewRating', {}).get('ratingValue')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('description')
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
