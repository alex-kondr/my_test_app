#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def Request(url):
    r = agent.Request(url, force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.demonews.de/games/spieletests/'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//h2[@class="card-title"]/a')
    for rev in revs:
        title = rev.xpath("text()").string()
        url = rev.xpath("@href").string()

        if url and title:
            session.queue(Request(url), process_review, dict(url=url, title=title))

    next_url = data.xpath('//a[@aria-label="Nächste Seite"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, context)


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Spiele'
    product.manufacturer = data.xpath('//dl[contains(dt/text(), "Entwickler")]/dd//text()').string(multiple=True)

    product.name = data.xpath('//div[@class="game-meta-label"]/text()').string()
    if not product.name:
        product.name = context['title'].split(' Review:')[0].replace('Review: ', '').replace('Tests: ', '').strip()

    platform = data.xpath('//dl[contains(dt/text(), "Plattform")]/dd//text()').string()
    if platform:
        product.category += '|' + platform

    review = Review()
    review.type = 'pro'
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div/@data-pagefind-meta').string()
    if date:
        review.date = date.split('T')[0].split(':')[-1]

    author = data.xpath('//span[@class="meta-unit" and contains(text(), "VON")]/*/text()').string()
    author_url = data.xpath('//span[@class="meta-unit" and contains(text(), "VON")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].strip(' #')
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//div[@class="pros"]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–►…')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="cons"]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–►…')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="intro-paragraph"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[@class="fazit"]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="main-frame"]/p[not(@class)]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
