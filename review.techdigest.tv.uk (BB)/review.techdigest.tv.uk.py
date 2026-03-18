#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ["ABOUT US"]


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
    r = agent.Request(url, proxies=['rotating-us'], use='curl')
    return r


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.techdigest.tv/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath("//ul[@id='primary-menu']/li")
    for cat in cats:
        name = cat.xpath("a/text()").string()

        if name not in XCAT:
            cats1 = cat.xpath("ul/li")
            if cats1:
                for cat1 in cats1:
                    cat1_name = cat1.xpath("a/text()").string()

                    subcats = cat1.xpath("ul/li")
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.xpath("a/text()").string()
                            url = subcat.xpath("a/@href").string()
                            session.queue(Request(url), process_revlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                    else:
                        url = cat1.xpath("a/@href").string()
                        session.queue(Request(url), process_revlist, dict(cat=name+'|'+cat1_name))
            else:
                url = cat.xpath("a/@href").string()
                session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//h3[contains(@class, "title")]/a')
    for prod in prods:
        title = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url), process_product, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('HANDS-ON REVIEW: ', '').replace('Review: ', '')
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '').replace('_review', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "author") and not(contains(., "(Display Name not set)"))]//text()').string()
    author_url = data.xpath('//span[contains(@class, "author") and not(contains(., "(Display Name not set)"))]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath("//*[regexp:test(., 'verdict|conclusion', 'i')]/following-sibling::p//text()").string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="entry-content"]/p[not(regexp:test(., "For more information|For latest tech stories go to|For the full story") or preceding::*[regexp:test(., "verdict|conclusion", "i")])]//text()').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
