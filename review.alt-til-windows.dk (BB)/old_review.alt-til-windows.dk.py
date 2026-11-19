#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://alt-til-windows.dk/nyheder/', use='curl', force_charset='utf-8'), process_revlist, {})


def process_revlist(data: Response, context: dict[str, str], session: Session):
    for rev in data.xpath("//h3[@class='entry-title td-module-title']/a[contains(., 'nmeldelse')]"):
        name = rev.xpath("text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(name=name, url=url))

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next, use='curl', force_charset='utf-8'), process_revlist, {})


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name'].replace('Anmeldelse af ', '').split('anmeldelse')[0]
    product.url = context['url']
    product.category = 'Software'
    product.ssid = context['url'].split('/')[-2]

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//span[@class='td-post-date']//text()").string()

    summary = data.xpath("//div[contains(@class, 'td-post-content')]/p[1]//text()").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))

    conclusion = data.xpath("//*[regexp:test(., 'Konklusion|Bedømmelsen')]/following::p[1]/text()").string()
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    excerpt = data.xpath("//div[contains(@class, 'td-post-content')]//text()").string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.split(summary)[-1]
        if conclusion:
            excerpt = excerpt.split(conclusion)[0]
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    pros = data.xpath("//div[contains(@class, 'td-post-content')]/p[contains(., 'Fordele')]/following::ul[1]/li/text()").strings()
    if pros:
        for pro in pros:
            review.properties.append(ReviewProperty(type='pros', value=pro))
    else:
        pros = data.xpath("//div[contains(@class, 'td-post-content')]/*[contains(., 'Positivt:')]/following::p[1]//text()").string(multiple=True)
        if pros:
            for pro in [pro for pro in pros.split('– ') if pro]:
                review.properties.append(ReviewProperty(type='pros', value=pro))

    cons = data.xpath("//div[contains(@class, 'td-post-content')]/p[contains(., 'Ulemper')]/following::ul[1]/text()").strings()
    if cons:
        for con in cons:
            review.properties.append(ReviewProperty(type='cons', value=con))
    else:
        cons = data.xpath("//div[contains(@class, 'td-post-content')]/*[contains(., 'Negativt:')]/following::p[1]").string(multiple=True)
        if cons:
            for con in [con for con in cons.split('– ') if con]:
                review.properties.append(ReviewProperty(type='cons', value=con))

    author = data.xpath("//div[@class='td-post-author-name']/a").first()
    if author:
        author_url = author.xpath("@href").string()
        author_name = author.xpath("text()").string()
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author_name, url=author_url, ssid=author_ssid))

    product.reviews.append(review)
    session.emit(product)
