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
    cats = data.xpath('//li[contains(@class, "menu-item-object-product_cat menu-item-has-children")]')
    for cat in cats:
        url = cat.xpath('a/@href').string()
        name = cat.xpath('a//text()').string()

        if not session.seen(url):
            subcats = cat.xpath('ul/li/a')

            if len(subcats) == 1:
                session.queue(Request(url), process_prodlist, dict(cat=name))

            for subcat in subcats:
                url = subcat.xpath('@href').string()
                subcat_name = subcat.xpath('.//text()').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//p[contains(@class, "name product-title")]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.manufacturer = data.xpath('//th[contains(., "Brand")]/following-sibling::td[1]//p//text()').string() or data.xpath('//th[contains(., "Manufacturer")]/following-sibling::td[1]/p//text()').string()
    product.ssid = product.url.split('/')[-2]

    mpn = data.xpath('//span[@class="sku"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//th[contains(., "GTIN")]/following-sibling::td[1]/p//text()').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//ol[@class="commentlist"]/li')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@id').string().split('-')[-1]

        date = rev.xpath('.//time/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//strong[contains(@class, "author")]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//strong[@class="rating"]/text()').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//div[@class="description"]/p//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            if not session.seen(review.ssid):
                product.reviews.append(review)

    if product.reviews:
        session.emit(product)
