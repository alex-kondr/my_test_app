#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


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
    r = agent.Request(url, proxies=['rotating-us'], use='curl', force_charset='utf-8')
    return r


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.booredatwork.com/category/review/'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//div/@data-next-page').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' Review – ')[0].replace('Review: ', '').replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]

    product.category = data.xpath('//a[contains(@class, "terms-list-item") and not(regexp:test(., "Review|New|Tech"))]/text()').string()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//span[contains(@class, "type-date")]/time/text()').string()

    author = data.xpath('//span[contains(@class, "type-author")]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//h4[contains(., "Final Thoughts")]/following-sibling::p[not(contains(., "We were provided with "))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h4[contains(., "Final Thoughts")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "container")]/p[not(contains(., "We were provided with "))]/text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
