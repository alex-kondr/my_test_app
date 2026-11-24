#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.queue(Request('http://www.androidguys.com/category/reviews/'), process_revlist, dict())
    # session.queue(Request('https://www.androidguys.com/reviews/accessory-reviews/godice-smart-connected-dice/'), process_product, dict(url="https://www.androidguys.com/reviews/accessory-reviews/godice-smart-connected-dice/", name="name"))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath("//div[contains(@class,'wpb_column vc_column_container tdc-column td-pb-span8')]//h3[@class='entry-title td-module-title']/a")
    for rev in revs:
        name = rev.xpath(".//text()").string()
        url = rev.xpath("@href").string()
        if name and url and not session.seen(url):
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath("//link[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name'].split(' Review')[0].split(' review')[0]
    product.ssid = context['url'].split('/')[-2]
    product.category = data.xpath("//li[@class='entry-category']/a//text()").string()
    product.url = context['url']

    review = Review()
    review.title = context['name']
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']
    review.date = data.xpath("//time[contains(@class,'entry-date')]/@datetime").string().split('T')[0]

    author = data.xpath("//div[@class='td-author-name vcard author']//a").first()
    if author:
        author_name = author.xpath(".//text()").string()
        author_url = author.xpath("@href").string()
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))

    grades = data.xpath("//tr[@class='td-review-row-stars']")
    for grade in grades:
        grade_name = grade.xpath(".//td[@class='td-review-desc']//text()").string()
        grade_val = len(grade.xpath(".//i[@class='td-icon-star']"))

        if grade.xpath(".//i[@class='td-icon-star-half']"):
            grade_val += 0.5

        if grade_name != 'Overall':
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    grade_overall = data.xpath("//div[@class='td-review-final-score']//text()").string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    excerpt = data.xpath("//div[@class='td-post-content tagdiv-type']//p//text()").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

        product.reviews.append(review)
        session.emit(product)
