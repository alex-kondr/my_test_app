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
    r = agent.Request(url, proxies=['eu'])
    return r


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.chip.de/testberichte'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//section[not(h2[contains(text(), "Die beliebtesten Testberichte")])]//article[h3]//a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' im CHIP-Test: ')[0].split(' im Test')[0].replace(' im Praxistest', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('_')[-1].replace('.html', '')

    product.category = data.xpath('//li[@class="BreadcrumbList__Item"]/a[not(contains(., "Test"))]/text()').string()
    if not product.category:
       product.category = 'Technik'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@itemprop="author"]//text()').string(multiple=True)
    author_url = data.xpath('//span[@itemprop="author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('_')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//li[contains(., "Testurteil")]/p[@class="QuickFacts__Body"]/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.split()[-1].strip('( )').replace(',', '.'))
        if grade_overall > 0:
            review.grades.append(Grade(type='overall', value=grade_overall, best=1.0, worst=5.0))

    grades = data.xpath('//section[@class="TestRating__Results"]//div[@class="TestRating__CategoryToggle"]')
    for grade in grades:
        grade_name = grade.xpath('span/text()').string()
        grade_val = grade.xpath('span[contains(., "(")]/text()').string(multiple=True)
        if grade_name and grade_val:
            grade_val = float(grade_val.split()[-1].strip('( )').replace(',', '.'))
            if grade_val > 0:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=1.0, worst=5.0))

    pros = data.xpath('//dl[contains(@class, "is-pro")]/dd')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//dl[contains(@class, "is-con")]/dd')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//header/h2//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[h2[contains(text(), "Fazit")]]/p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//section[@id]/div/p[not(regexp:test(., "Testcenter:|Redaktion:"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
