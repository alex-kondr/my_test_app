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
    session.queue(Request("https://theheadphonelist.com/category/reviews/"), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//nav//li[contains(a, "Reviews")]/ul/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if url and not session.seen(url):
            session.queue(Request(url), process_review, dict(context, title=title, url=url))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split('– A Review of the ')[-1].split(' – A Review of ')[-1].split(' Review : ')[0].replace('Review: ', '').split(' review')[0].split(' Review')[0]
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="author"]/@content').string()
    author_url = data.xpath('//li[@itemprop="author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//strong[contains(., "Verdict ")][contains(., "/")]//text()').string()
    if grade_overall and "/" in grade_overall:
        grade_val = grade_overall.split('/')[0].split('– ')[-1].split('Verdict ')[-1]
        grade_max = grade_overall.split('/')[-1].rstrip(',')
        if grade_val and grade_val[0].isdigit() and float(grade_val) > 0 and grade_max and grade_max[0].isdigit():
            review.grades.append(Grade(type='overall', value=float(grade_val), best=float(grade_max)))

    pros = data.xpath('(//p[contains(., "Pros:")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–►…')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p[contains(., "Cons:")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–►…')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "widget-containe")]/p[contains(@class, "has-vivid-cyan-blue")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[contains(strong, "CONCLUSION")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[contains(strong, "CONCLUSION")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "widget-containe")]/p[not(@class)]//text()').string(multiple=True)

    pages = data.xpath('//div[contains(@class, "page-links")]/a')
    if pages:
        product_dict = dict()
        product_dict['name'] = product.name
        product_dict['url'] = product.url
        product_dict['ssid'] = product.ssid
        product_dict['category'] = product.category

        review_dict = dict()
        review_dict['title'] = review.title
        review_dict['date'] = review.date
        review_dict['author'] = author
        review_dict['author_url'] = author_url
        review_dict['grade_overall'] = grade_overall
        review_dict['pros'] = pros
        review_dict['cons'] = cons
        review_dict['summary'] = summary
        review_dict['excerpt'] = excerpt

        review_dict['pages'] = [dict(title=review.title+'- Page 1', url=data.response_url)]
        for page in pages:
            page_num = page.xpath('span/text()').string()
            page_url = page.xpath('@href').string()
            review_dict['pages'].append(dict(title=review.title+'- Page '+page_num, url=page_url))

        session.queue(Request(page_url), process_review_last, dict(product=product_dict, review=review_dict))

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_last(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']
    product.category = context['product']['category']

    review = Review()
    review.type = 'pro'
    review.title = context['review']['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = context['review']['date']

    author = context['review']['author']
    author_url = context['review']['author_url']
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = context['review']['grade_overall']
    if grade_overall and "/" in grade_overall:
        grade_val = grade_overall.split('/')[0].split('– ')[-1].split('Verdict ')[-1]
        grade_max = grade_overall.split('/')[-1].rstrip(',')
        if grade_val and grade_val[0].isdigit() and float(grade_val) > 0 and grade_max and grade_max[0].isdigit():
            review.grades.append(Grade(type='overall', value=float(grade_val), best=float(grade_max)))

    pros = data.xpath('(//p[contains(., "Pros:")]/following-sibling::*)[1]/li')
    if not pros:
        pros = context['review']['pros']

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–►…')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p[contains(., "Cons:")]/following-sibling::*)[1]/li')
    if not cons:
        cons = context['review']['cons']

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–►…')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = context['review']['summary']
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[contains(@class, "widget-containe")]/p[not(@class)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    pages = context['review']['pages']
    for page in pages:
        review.add_property(type='pages', value=page)

    excerpt = context['review']['excerpt']
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
