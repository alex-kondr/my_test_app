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
    r = agent.Request(url, proxies=['rotating-us'], force_charset='utf-8')
    return r


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://fotovilag.hu/content/index/cat/2'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//section//a[@class="more"]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(url=url))

    next_url = data.xpath('//a[contains(., "kovetkezo")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = data.xpath('(//section[contains(@class, "content")]/h1)[1]//text()').string()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = 'Foto'

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//section[contains(@class, "content")]/span[@class="mod-date"]/text()').string()

    author = data.xpath('//a[contains(@href, "blog.hu/user")]/text()').string()
    author_url = data.xpath('//a[contains(@href, "blog.hu/user")]/@href').string()
    if author and author_url:
        author_ssid = author_url.replace('/tab/msg', '').split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('(//section[contains(@class, "content")]/p[not(contains(., "Fotó: ©")) and text()]|//section[contains(@class, "content")]/blockquote|//h2/following-sibling::p)//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
