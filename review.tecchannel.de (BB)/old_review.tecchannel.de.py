#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def Request(url):
    options = "-H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:80.0) Gecko/20100101 Firefox/80.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'Connection: keep-alive' -H 'Upgrade-Insecure-Requests: 1' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: Trailers'"
    r = agent.Request(url, use='curl', options='-s -L --insecure '+options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.tecchannel.de/p/suche?query=im%20test&type=Artikel'), process_category, dict(page=1))


def process_category(data: Response, context: dict[str, str], session: Session):
    empty = True
    for link in data.xpath("//div[@class='row']/div[@class='col-sm-6']/h1/a"):
        empty = False
        url = link.xpath('@href').string()
        name = link.xpath('text()').string()
        if url and name and ('test' in name.lower() or 'hands' in name.lower()) and not session.seen(url):
            session.queue(Request(url), process_product, dict(context, url=url, name=name))

    if not empty:
        context['page'] += 1
        next = "https://www.tecchannel.de/p/suche?query=im%20test&type=Artikel&page=" + str(context['page'])
        session.queue(Request(next), process_category, context)


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name'].replace('Test:', '').replace('im Test', '').replace('Hands-On:', '')
    product.url = context['url']
    product.ssid = context['url'].split(',')[-1]

    product.category = data.content.split('tags: [')[-1].split(']')[0].replace(',', '|').replace('"', '')

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'

    review.date = data.xpath("//div[@class='idgArticleAuthors']/text()").string().replace('Von', '')

    author = data.xpath("//div[@class='idgArticleAuthors']/span/text()").string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    # Summary
    summary = data.xpath('//node()[regexp:test(name(),"h\d")][regexp:test(descendant::text(),"(TEST-FAZIT|Test-Fazit|Testergebnisse)")]/following-sibling::p[string-length(normalize-space(.))>100][1]//text()').string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))

    # Excerpt
    excerpt = data.xpath('//div[@class="abstract"]//text()').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = ''.join(excerpt.split(summary))

        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
        product.reviews.append(review)
        session.emit(product)
