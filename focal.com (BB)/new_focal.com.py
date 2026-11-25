#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ['Custom & Integration', 'Products', 'Our lookbooks', 'Automotive partnerships']


def Request(url):
    r = agent.Request(url, use='curl')
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.focal.com/en/collections'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//div[@data-type="1"]//div[contains(@class, "col-")]')
    for cat in cats:
        name = cat.xpath('.//div[@class="indexBlock-title box-title"]/a//text()').string() or cat.xpath('.//span[@class="hoverSimple-text"]//text()').string()
        url = cat.xpath('a/@href').string()
        cats1 = cat.xpath('.//div[@class="indexBlock-title box-title"]/following-sibling::div[@class="indexBlock-cols clearfix"]/a')

        if cats1:
            for cat1 in cats1:
                cat1_name = cat1.xpath('following-sibling::p[1]//text()').string(multiple=True)
                url = cat1.xpath('@href').string()
                if cat1_name not in XCAT:
                    session.queue(Request(url), process_category, dict(cat=name + "|" + cat1_name))

        elif name not in XCAT:
            session.queue(Request(url), process_category, dict(cat=name))


def process_category(data: Response, context: dict[str, str], session: Session):
    subcats_url = data.xpath('//a[@class="box box-full hoverSimple"]/@href').string()
    if subcats_url:
        session.queue(Request(subcats_url), process_prodlist, dict(context))
    else:
        process_prodlist(data: Response, context: dict[str, str], session: Session)


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//div[@data-type="3"]/div | //div[a[contains(text(), "See the product")]]')
    for prod in prods:
        name = prod.xpath('.//h3//text()').string()
        url = prod.xpath('a/@href').string()
        
        session.queue(Request(url), process_product, dict(context, name=name, url=url))
    
    # loaded all prods


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.ssid = product.url.split('/')[-1]
    product.manufacturer = 'Focal'

    revs = data.xpath('//div[@class="review"]')
    if not revs:
        return

    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('span/@data-review').string()
        review.date = rev.xpath('.//div[@class="review-date"]//text()').string()

        author = rev.xpath('.//div[@class="review-name"]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[contains(@class, "rate")]/@class').string()
        if grade_overall:
            grade_overall = float(grade_overall.split('-')[-1])
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        excerpt = rev.xpath('.//p[@class="review-p"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)
    
    if product.reviews:
        session.emit(product)
