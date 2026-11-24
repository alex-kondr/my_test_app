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
    session.queue(Request('https://androidguys.com/category/reviews/'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//h3[contains(@class, "post_title")]/a')
    for rev in revs:
        name = rev.xpath('.//text()').string()
        url = rev.xpath('@href').string()
        if name and url and not session.seen(url):
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name'].split(' Review')[0].split(' review')[0].strip()
    product.url = context['url']
    product.ssid = product.url.rstrip('/').split('/')[-1]

    category = data.xpath('//div[contains(@class, "meta_category")]//a/text()').string()
    if category:
        product.category = category.replace(' Reviews', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "meta_container")]//div[contains(@class, "meta_author")]//a/text()').string()
    author_url = data.xpath('//div[contains(@class, "meta_container")]//div[contains(@class, "meta_author")]//a/@href').string()
    if author and author_url:
        author_ssid = author_url.rstrip('/').split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[contains(@class, "score_value")]/text()').string()
    if grade_overall and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    # Витончений підрахунок зірок через XPath: повні зірки + половинки div 2
    grades = data.xpath('//div[contains(@class, "reviewscore")]/ul/li')
    for grade in grades:
        grade_name = grade.xpath('strong/text()').string()
        grade_val = grade.xpath('count(.//i[@class="fa fa-star"]) + count(.//i[@class="fa fa-star-half-o"]) div 2')
        if grade_name and float(grade_val) > 0:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('//div[contains(@class, "conspros")][h3[contains(., "PROS")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–►…')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "conspros")][h3[contains(., "CONS")]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–►…')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    # Розумний фолбек: якщо є і conclusion і summary — зберігаємо обидва; якщо тільки desc — записуємо в conclusion
    conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    summary = data.xpath('//div[@class="desc"]/p//text()').string(multiple=True)
    if summary and conclusion:
        review.add_property(type='summary', value=summary)
    elif summary:
        review.add_property(type='conclusion', value=summary)

    excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content-inner")]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
