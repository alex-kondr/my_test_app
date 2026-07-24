from agent import *
from models.products import *


XCAT = ['Home', 'Impressum']


def run(context, session):
    session.queue(Request('https://www.nextgen.at/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@id="menu-menu"]/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if ' Angebot' not in title:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//li[contains(@class, "next_paginate_link")]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' Test: ')[0].strip()
    product.ssid = data.xpath('//article[contains(@class, "post")]/@id').string().split('-')[-1]
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[@class="post-inner-wrapper" or contains(@class, "inner-container")]/p[regexp:test(., "^Hersteller:")]/a/text()').string()

    prod_url = data.xpath('//a[contains(@rel, "sponsored") or contains(@href, "amzn")]/@href').string()
    if not prod_url:
        prod_url = data.xpath('//div[@class="post-inner-wrapper"]//*[contains(text(), "amzn")]/text()').string()
    if not prod_url:
        prod_url = context['url']

    product.url = prod_url.split('url=')[-1].split()[0].strip('"”” ')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[contains(@property, "published_time")]/@content').string()
    if date:
        review.date = date.split('T')[0]

    excerpt = data.xpath('//div[@class="post-inner-wrapper" or contains(@class, "inner-container")]/p[not(contains(., "id=") or regexp:test(., "^Hersteller:") or contains(., "su_") or contains(., "Link: "))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="post-inner-wrapper"]/div[not(@class)]/p[not(contains(., "id=") or regexp:test(., "^Hersteller:") or contains(., "su_") or contains(., "Link: "))]//text()').string(multiple=True)

    if excerpt and excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
