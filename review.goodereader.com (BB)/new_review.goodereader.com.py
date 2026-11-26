#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XTITLE = [' the best ', ' vs ']


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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://goodereader.com/blog/category/reviews'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//div[@class="post-outer"]')
    for rev in revs:
        title = rev.xpath('.//h2//text()').string(multiple=True)
        url = rev.xpath('a[@class="post-link"]/@href').string()

        if title and url and not any(xtitle not in title for xtitle in XTITLE):
            session.queue(Request(url), process_review, dict(title=title, url=url))

    # next_url = data.xpath('//link[@rel="next"]/@href').string()
    # if next_url:
    #     session.queue(Request(next_url), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = data.xpath('//h2[@class="cwp-item"]//text()').string() or context['title']
    product.url = context['url']
    product.category = 'E-Book Readers'

    shortlink = data.xpath('//link[@rel="shortlink"]/@href').string()
    if shortlink and '?p=' in shortlink:
        product.ssid = shortlink.split('?p=')[-1]
    else:
        product.ssid = product.url.rstrip('/').split('/')[-1].replace('-review', '')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]//text()').string(multiple=True)
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.rstrip('/').split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "review-wu-grade-content")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.split('/')[0].strip()
        try:
            grade_overall = float(grade_overall)
            if grade_overall > 0:
                grade_best = 10.0 if grade_overall > 5 else 5.0
                review.grades.append(Grade(type='overall', value=grade_overall, best=grade_best))
        except:
            pass

    grades = data.xpath('//div[contains(@class, "rev-option")]')
    for grade in grades:
        grade_name = grade.xpath('.//h3//text()').string(multiple=True)
        grade_val = grade.xpath('.//span[contains(., "/")]//text()').string(multiple=True)
        if grade_name and grade_val:
            grade_val, grade_best = grade_val.split('/')
            try:
                if float(grade_val) > 0:
                    review.grades.append(Grade(name=grade_name, value=float(grade_val), best=float(grade_best)))
            except:
                continue

    pros = data.xpath('//div[contains(@class, "pros")]//ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(u' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "cons")]//ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(u' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h3[contains(., "Wrap up") or contains(., "Wrap Up") or contains(., "My Thoughts")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Wrap up") or contains(., "Wrap Up") or contains(., "My Thoughts")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]/p//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.strip()
        if len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
