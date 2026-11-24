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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://eftm.com/tag/review'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//article//h2/a')
    for rev in revs:
        title = rev.xpath('.//text()').string()
        url = rev.xpath('@href').string()

        if url and title and not session.seen(url):
            session.queue(Request(url), process_product, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' review:')[0].split(' Review:')[0].split(' –')[0].split(' -')[0].replace('REVIEW:', '').replace('Review:', '').replace('REVIEW', '').replace('Review', '').replace('review', '').strip(' :–-')
    product.url = context['url']
    product.ssid = product.url.rstrip('/').split('-')[-1]

    product.category = data.xpath('//div[contains(@class, "byline")]//a[contains(@href, "/category/") and not(contains(text(), "Reviews"))]/text()').string()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "byline")]//a[contains(@href, "/author/")]/text()').string()
    author_url = data.xpath('//div[contains(@class, "byline")]//a[contains(@href, "/author/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.rstrip('/').split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "review-summary-score-box")]//h4/text()').string()
    if grade_overall:
        grade_overall = grade_overall.replace('%', '').strip()
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//div[contains(@class, "review-breakdowns")]//div[contains(@class, "review-breakdown")]')
    for grade in grades:
        grade_name = grade.xpath('.//*[contains(@class, "title")]/text()').string()
        grade_val = grade.xpath('.//*[contains(@class, "score-text")]/text()').string()
        if grade_name and grade_val:
            grade_val = grade_val.replace('%', '').strip()
            if grade_val and float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100.0))

    conclusion = data.xpath('//h2[contains(., "Overall thoughts")]/following-sibling::p[not(ancestor::*[contains(@class, "review-summary") or contains(@class, "byline") or contains(@class, "social")] or contains(., "More details can be found"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[normalize-space(text())="Summary"]/following-sibling::p[not(ancestor::*[contains(@class, "review-summary") or contains(@class, "byline") or contains(@class, "social")] or contains(., "More details can be found"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    summary = data.xpath('//div[contains(@class, "review-summary-content")]/p//text()[not(contains(parent::strong, "Summary"))]').string(multiple=True)
    if summary and conclusion:
        review.add_property(type='summary', value=summary)
    elif summary:
        review.add_property(type='conclusion', value=summary)

    excerpt = data.xpath('//h2[contains(., "Overall thoughts")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[normalize-space(text())="Summary"]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//article//p[not(ancestor::*[contains(@class, "review-summary") or contains(@class, "byline") or contains(@class, "social")] or contains(., "More details can be found"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
