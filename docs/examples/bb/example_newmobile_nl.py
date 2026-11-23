#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from datetime import datetime


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
    session.queue(Request('http://www.nieuwemobiel.nl/Reviews'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//article/div[h3 or h2]')
    for rev in revs:
        title = rev.xpath('.//a/text()').string()
        date = rev.xpath('div/span/text() | div/text()').string()
        url = rev.xpath('.//a/@href').string()
        session.queue(Request(url), process_review, dict(title=title, date=date, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' review')[0].split(' Review')[0].strip()
    product.url = context['url']
    product.ssid = product.url.rstrip('/').split('/')[-1]
    product.category = 'Mobiele telefoon'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = context.get('date')
    if date:
        parts = date.strip().split()
        if len(parts) == 2:
            date += ' ' + str(datetime.now().year)

        review.date = date

    author = data.xpath('//div[contains(@class, "card-body")]//a[contains(@href, "/redactie/")]/text()').string()
    author_url = data.xpath('//div[contains(@class, "card-body")]//a[contains(@href, "/redactie/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div/@aria-label[contains(., "Beoordeling:")]').string()
    if grade_overall:
        grade_overall = grade_overall.split(':')[-1].split(' van ')[0].strip()
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('//li[contains(span/text(), "Pluspunten:")]/text()').string()
    if pros:
        review.add_property(type='pros', value=pros)

    cons = data.xpath('//li[contains(span/text(), "Minpunten:")]/text()').string()
    if cons:
        review.add_property(type='cons', value=cons)

    summary = data.xpath('//section[h1]/p[contains(@class, "h5")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Conclusie")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusie")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="row"]/div/p[not(ancestor::footer)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
