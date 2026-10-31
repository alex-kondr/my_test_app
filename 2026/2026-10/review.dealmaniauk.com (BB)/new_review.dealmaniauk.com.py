#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def Request(url):
    r = agent.Request(url, force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://dealmaniauk.com'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//ul[contains(@class, "header-nav")]/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        subcats = cat.xpath('ul/li/a')
        for subcat in subcats:
            subcat_name = subcat.xpath('text()').string()
            url = subcat.xpath('@href').string()
            session.queue(Request(url), process_prodlist, dict(cat=name+'|'+subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//ul[contains(@class, "product_list")]/li')
    for prod in prods:
        name = prod.xpath('a/span/text()').string()
        url = prod.xpath('a/@href').string()

        rating = prod.xpath('.//strong[@class="rating"]/text()')
        if rating and not session.seen(url):
            session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']

    product.manufacturer = data.xpath('//tr[normalize-space(th/text())="Brand"]/td//text()').string()
    if not product.manufacturer:
        product.manufacturer = data.xpath('//tr[normalize-space(th/text())="Manufacturer"]/td//text()').string()

    mpn = data.xpath('//tr[normalize-space(th/text())="MPN"]/td//text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//tr[normalize-space(th/text())="gtin"]/td//text()').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//ol[@class="commentlist"]/li/div')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//time/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//strong[contains(@class, "author")]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//strong[contains(@class, "rating")]/text()').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//div[contains(@class, "description")]/p//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            ssid = rev.xpath('@id').string()
            if ssid:
                review.ssid = ssid.split('-')[-1]
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            if not session.seen(review.ssid):
                product.reviews.append(review)

    if product.reviews:
        session.emit(product)
