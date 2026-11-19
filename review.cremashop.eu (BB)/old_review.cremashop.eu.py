#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *

XCAT = ['Coffee', 'Delicacies', 'Gourmet Food', 'Spare Parts', 'Tea', 'Sweeteners and Coffee Add-Ins', 'Gifts and Seasonal Items']

def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.cremashop.eu/en/categories/'), process_frontpage, dict())

def process_frontpage(data: Response, context: dict[str, str], session: Session):
    for cat in data.xpath("//a[@class='link-dark']"):
        category = cat.xpath("preceding::h2[1]/text()").string()
        print category
        category2 = cat.xpath("text()").string()
        url = cat.xpath("@href").string()
        if url and category not in XCAT and category2:
            session.queue(Request(url), process_productlist, dict(category=category+'|'+category2))

def process_productlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath("//h4[regexp:test(@class,'product-title')]/a")
    cnt = 0
    for prod in prods:
        cnt += 1
        name = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        rated = prod.xpath("following::div[1]/div[@class='star-rating']/i")
        if rated:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath("//a[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_productlist, dict(context))

def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.sku = data.xpath("//li[regexp:test(.,'Product number')]/span/text()").string(multiple=True)
    product.ssid = product.sku
    product.category = context['category']
    product.url = context['url']
    product.manufacturer = data.xpath("//li[regexp:test(.,'Brand')]/a/text()").string(multiple=True)

    ean = data.xpath("//li[regexp:test(.,'EAN')]/span/text()").string(multiple=True)
    if ean:
        product.properties.append(ProductProperty(type='id.ean', value=ean))

    print 'revs --> ', data.xpath("//li[@class='nav-item'][regexp:test(.,'English')]/a/span[3]/text()").string()
    
    revs = data.xpath("//div[@id='reviews-en']//div[@data-review]")
    cnt = 0
    for rev in revs:
        cnt += 1
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.title = rev.xpath("h5/text()").string()
        review.ssid = rev.xpath("@data-review").string()
        print cnt, review.ssid

        review.date = rev.xpath("time/@datetime").string()
        author_name = rev.xpath("span/text()").string() or 'unknown'
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = rev.xpath("@data-rating").string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=int(grade_overall), best=5))

        excerpt = rev.xpath("p//text()").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
