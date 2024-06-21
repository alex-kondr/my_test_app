#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def run(context, session):
   session.queue(Request('http://www.brasilgamer.com.br/archive/reviews'), process_revlist, dict(page=1))


def process_revlist(data, context, session):
    for link in data.xpath('//p[@class="title"]//a'):
        url = link.xpath('@href').string()
        name = link.xpath('text()').string()
        if url and name:#and not session.seen(url):
            bad_list = [' review: ',' review ',' Review ', ' - ']
            for item in bad_list:
                if item in name:
                    namex = name.split(item)[0]
                    if len(namex) == 0:
                        name = name.split(item)[1]
                    else:
                        name = namex
                    break
            session.queue(Request(url), process_review, dict(context, url=url, name=name))

    # Next page
    next=data.xpath('//div[@class="next"]/a[1]//@href').string()
    if next:
        session.queue(Request(next), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.category = data.xpath('//div[@class="tagged_with"]//li//text()[string-length(normalize-space(.))>1]').join('|')
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('.pt/')[1]

    review = Review()
    review.type = 'pro'
    review.url = context['url']
    review.ssid = review.title
    review.ssid = product.ssid + ' review '

    review.date = data.xpath('//meta[@property="article:published_time"]//@content').string(multiple=True)
    if review.date:
        if 'T' in review.date: review.date = review.date.split('T')[0]
        review.ssid += review.date

    author = data.xpath('//div[@class="author"]//span[@class="name"]//text()[string-length(normalize-space(.))>1]').string()
    if author:
        review.ssid += author
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//node()[regexp:test(name(),"h\d")][regexp:test(descendant::text(),"(veredic|Veredic)")]/following-sibling::p//text()').string(multiple=True) or data.xpath('//span[@class="strapline"]//text()').string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))

    excerpt = data.xpath('//meta[@property="og:description"]//@content').string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    product.reviews.append(review)

    if product.reviews:
        session.emit(product)

