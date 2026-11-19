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
    r = agent.Request(url, force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://alt-til-windows.dk/category/programmer/'), process_revlist, dict(cat='Programmer'))
    session.queue(Request('https://alt-til-windows.dk/category/gaming/'), process_revlist, dict(cat='Spele'))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//div[contains(h3/@class, "entry-title")]')
    for rev in revs:
        title = rev.xpath("h3/a/text()").string()
        cat = rev.xpath('.//a[contains(@class, "post-category")]/text()').string()
        url = rev.xpath("h3/a/@href").string()
        session.queue(Request(url,), process_review, dict(cat=context['cat']+'|'+cat, title=title, url=url))

    next = data.xpath('//a[@aria-label="next-page"]/@href').string()
    if next:
        session.queue(Request(next), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.url = context['url']
    product.name = context['title'].split(' — ')[0].strip()
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']
    product.manufacturer = data.xpath('//li[contains(., "Udvikler:")]/a/text()').string(multiple=True)

    review = Review()
    review.type = 'pro'
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "author-name")]/text()').string()
    author_url = data.xpath('//a[contains(@class, "author-name")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//div[contains(@class, "block-inner")]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
