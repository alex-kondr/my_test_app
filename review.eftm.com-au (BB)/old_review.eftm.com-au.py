#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


import _proxies_config
reload(_proxies_config)
PROXIES = _proxies_config.us_rotating_proxies + _proxies_config.eu_rotating_proxies + _proxies_config.ap_rotating_proxies


def Request(url, page=0):
    r = agent.Request(url, use='curl', options='', proxies=PROXIES, max_age=0)
    r.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://eftm.com/tag/review'), process_revlist, dict(context, page=1))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath("//li[@class='infinite-post']/a")
    for rev in revs:
        url = rev.xpath("@href").string()
        name = rev.xpath("@title").string()
        if name and url and not session.seen(url):
            session.queue(Request(url), process_product, dict(context, name=name, url=url))
    
    if revs:
        next_page = context['page'] + 1
        next_url = 'https://eftm.com/tag/review/page/' + str(next_page)
        session.queue(Request(next_url), process_revlist, dict(context, page=next_page))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name'].split(' Review')[0].split(' review')[0]
    product.ssid = context['url'].split('/')[-1]
    product.url = context['url']
    product.category = data.xpath("//a[@class='post-cat-link']/span//text()").string()
    
    review = Review()
    review.title = context['name']
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']
    review.date = data.xpath("//time/@datetime").string()
    
    authors = data.xpath("//a[@rel='author']")
    for author in authors:
        author_name = author.xpath(".//text()").string()
        author_url = author.xpath("@href").string()
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))
    
    excerpt = data.xpath("//div[@id='content-main']//p//text()").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
    
        product.reviews.append(review)
        session.emit(product)
    