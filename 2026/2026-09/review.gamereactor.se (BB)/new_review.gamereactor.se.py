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
    r = agent.Request(url, proxies=['rotating-eu'], force_charset='utf-8')
    return r


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.gamereactor.se/recensioner/'), process_revlist, dict(cat='Spel'))
    session.queue(Request('http://www.gamereactor.se/hardvara/'), process_revlist, dict(cat='Hårdvara'))
    session.queue(Request('http://www.gamereactor.se/blu-ray/'), process_revlist, dict(cat='Blu-ray'))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('(//main[@id="main-content"]/div/a|//a[@class="gn-story" or @class="gn-dayrow"])/@href')
    for rev in revs:
        url = rev.string()
        session.queue(Request(url), process_review, dict(context, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.url = context['url']
    product.ssid = data.xpath('//article/@data-id').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[contains(@class, "side-sticky")]//div[contains(span, "Utvecklare")]/span[not(contains(., "Utvecklare"))]/text()').string(multiple=True)

    title = data.xpath('//h1/text()').string()
    product.name = data.xpath('//section[contains(@class, "gameinfo")]/h2/a/text()').string()
    if not product.name:
        product.name = title

    platforms = data.xpath('//div[contains(span, "Plattformar")]/div/span/text()').join('/')
    if platforms:
        product.category += '|' + platforms

    genres = data.xpath('//div[contains(@class, "side-sticky")]//div[contains(span, "Genre")]/span[not(contains(., "Genre"))]/text()').join('/')
    if genres:
        product.category += '|' + genres

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "revbyline")]/a[contains(@href, "/author/")]//text()').string(multiple=True)
    author_url = data.xpath('//div[contains(@class, "revbyline")]/a[contains(@href, "/author/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "side-sticky")]/div/div/span/text()[regexp:test(., "^\d{1,2}$")]').string()
    if not grade_overall:
        grade_overall = data.xpath('//div[@class="gr-verdict"]/div/div/span/text()[regexp:test(., "^\d{1,2}$")]').string()

    if grade_overall and grade_overall.isdigit() and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pro = data.xpath('//div[@class="gr-verdict"]//div[contains(span, "Fördelar")]/span[not(contains(., "Fördelar"))]/text()').string()
    if pro:
        review.add_property(type='pros', value=pro)

    con = data.xpath('//div[@class="gr-verdict"]//div[contains(span, "Nackdelar")]/span[not(contains(., "Nackdelar"))]/text()').string()
    if con:
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[div/h1]/div[not(a)]/span//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@id="page0"]/p//text()').string(multiple=True)
    if excerpt:
        excerpt = re.sub(r'<.*?>', '', excerpt).replace('<bild<', '').replace('" target="_blank">', '').replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
