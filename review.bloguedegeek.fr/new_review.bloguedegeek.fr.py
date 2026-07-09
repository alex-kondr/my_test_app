from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://bloguedegeek.net/posts/', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if title and '[Test]' in title:
            session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' [Test]', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-test', '')
    product.category = 'Technologie'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[h1]//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@class="post__author__name"]/text()').string()
    author_url = data.xpath('//a[@class="post__author__name"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//button[contains(@class, "total-score")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//div[contains(@id, "progress-bar")]/div[@class="progress-name"]')
    for grade in grades:
        grade_name = grade.xpath('text()').string()
        grade_val = grade.xpath('(following-sibling::*)[1][@class="progress-score"]/text()').string()
        if grade_name and grade_val and grade_val[0].isdigit() and float(grade_val) > 0:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('(//p[contains(strong, "Points positifs")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p[contains(strong, "Points négatifs")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p[not(contains(strong, "Points positifs") or contains(strong, "Points négatifs"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p[not(contains(strong, "Points positifs") or contains(strong, "Points négatifs"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="post__content"]/p[not(contains(strong, "Points positifs") or contains(strong, "Points négatifs"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
