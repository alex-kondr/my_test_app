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
    r = agent.Request(url, proxies='eu')
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://hwtech.ru/?s=%D0%BE%D0%B1%D0%B7%D0%BE%D1%80'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//article//h3[contains(@class, "article-title")]/a')
    for rev in revs:
        title = rev.xpath("text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_product, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = product.url.rstrip('/').split('/')[-1].replace('.html', '')
    product.category = u'Обзор и тестирование'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.ssid = product.ssid
    review.url = context['url']
    review.date = data.xpath('//div[h1]//span[contains(@class, "posts-date")]/a/text()').string()

    author = data.xpath(u'//p[contains(text(), "Статью подготовил и опубликовал")]/strong/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "entry-content")]//text()[contains(., "из 5") or contains(., "из 10") or contains(., "балл")][normalize-space(.)]').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.split(':')[-1].split()[0]
        if grade_overall and grade_overall.isdigit() and float(grade_overall) > 0:
            if float(grade_overall) > 5:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))
            else:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath(u'//p[contains(strong, "Плюсы продукта")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath(".//text()").string()
        if pro:
            pro = pro.strip(' +-*.:;•,–►…')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath(u'//p[contains(strong, "Минусы продукта")]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath(".//text()").string()
        if con:
            con = con.strip(' +-*.:;•,–►…')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="post-excerpt"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath(u'//h2[contains(., "Итоги")]/following-sibling::p[not(contains(., "За предоставленные на тестирование") or contains(., "Статью подготовил и опубликовал") )]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath(u'//h2[contains(., "Итоги")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath(u'//div[@class="entry-content"]/p[not(contains(., "За предоставленные на тестирование") or contains(., "Статью подготовил и опубликовал"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
