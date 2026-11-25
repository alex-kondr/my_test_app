#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = [u'Аналитика и полезная информация']


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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.ixbt.com/mobilepc/'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//div[h1]/div[not(@data-testid)]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name and url and name not in XCAT:
            session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//section//a[contains(@class, "publication-canonical-link")]/@href')
    for rev in revs:
        url = rev.string()

        if url and not session.seen(url):
            session.queue(Request(url), process_review, dict(context, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    title = data.xpath('//header//h1//text()').string()

    product = Product()
    product.name = data.xpath('//th[@colspan="3"]//text()').string(multiple=True) or title
    product.url = context['url']
    product.ssid = product.url.rstrip('/').split('/')[-1].replace('.shtml', '').replace('.html', '').replace('-review', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    authors = data.xpath('//a[contains(@href, "/authors/author/")]')
    for author in authors:
        author_name = author.xpath('.//text()').string(multiple=True)
        author_url = author.xpath('@href').string()
        if author_name and author_url:
            author_ssid = author_url.rstrip('/').split('/')[-1]
            review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

    pros = data.xpath(u'(//*[contains(., "Плюсы") or contains(., "Достоинства")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(u' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath(u'(//*[contains(., "Минусы") or contains(., "Недостатки")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(u' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath(u'//h3[contains(., "Вывод") or contains(., "Итог") or contains(., "Заключение")]/following-sibling::p[not(@class or contains(., "Плюсы") or contains(., "Достоинства") or contains(., "Минусы") or contains(., "Недостатки") or contains(., "В заключение предлагаем посмотреть") or preceding::*[contains(., "Добавить комментарий") or @name="comments"])]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath(u'//h3[contains(., "Вывод") or contains(., "Итог") or contains(., "Заключение")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath(u'//div[contains(@id, "publication")]/p[not(@class or contains(., "Плюсы") or contains(., "Достоинства") or contains(., "Минусы") or contains(., "Недостатки") or contains(., "В заключение предлагаем посмотреть") or preceding::*[contains(., "Добавить комментарий") or @name="comments"])]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.strip()
        if len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
