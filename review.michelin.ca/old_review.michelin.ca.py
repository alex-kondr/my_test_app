#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *

import time, random

debug = True

def run(context, session):
    session.sessionbreakers=[SessionBreak(max_requests=10000)]
    session.queue(Request('http://www.michelin.ca/CA/en/all-reviews.user.html'), process_category, dict(category='Tires'))

def process_category(data, context, session):
    for link in data.xpath('//select[@id="user-landing-select"]//option'):
        url=link.xpath('@value').string()
        name=link.xpath('text()').string()
        if url and name:
            purl = 'http://www.michelin.ca/CA/en/tires/products/' + url + '.html'
            url = 'http://www.michelin.ca/CA/en/all-reviews.' + url + '.user.html'
            session.queue(Request(url),process_product,dict(context,url=url,name=name,purl=purl))

def process_product(data, context, session):
    product=Product()
    product.name=context['name']
    product.url=context['purl']
    product.ssid=product.name + product.url
    product.category=context['category']
    product.manufacturer='Michelin'

    process_reviews(data, dict(context, product=product, c=0), session)

    if product.reviews:
        session.emit(product)

    time.sleep(random.randint(10,20))

def process_reviews(data, context, session):
    product = context['product']
    c=context['c']
    for link in data.xpath('//div[@class="inner BVinner"]'):
        c += 1
        review=Review()
        review.product=product.name
        review.url=context['url']
        review.ssid=product.ssid + ' review ' + str(c)
        review.type='user'

        # Title
        title = link.xpath('descendant::h3//text()').string()
        if title:
            review.title = title

        # Publish date
        pub_date=link.xpath('descendant::span[@class="on"]//text()').string()
        if pub_date:
            review.date=pub_date
        else:
            review.date='unknown'

        # Author
        author=link.xpath('descendant::span[@class="nickname"]//text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))
        else:
            review.authors.append(Person(name='unknown', ssid='unknown'))

        # Grades
        overall=link.xpath('descendant::div[@data-score]//@data-score').string()
        if overall:
            review.grades.append(Grade(name='Overall Rating', type='overall', value=overall, best=5))

        # Summary
        summary=link.xpath('descendant::p[@class="BVrevText"]//text()').string(multiple=True)
        if summary:
            review.properties.append(ReviewProperty(type='summary',value=summary))

            product.reviews.append(review)

    next = data.xpath('//a[@title="Next"]//@href').string()
    if next:
        context['c'] = c
        time.sleep(random.randint(10,15))
        session.do(Request(next), process_reviews, dict(context))
