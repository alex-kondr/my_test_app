#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *

debug = True

def run(context, session):
    session.sessionbreakers=[SessionBreak(max_requests=10000)]
    session.browser.agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
    session.queue(Request('https://computertotaal.nl/artikelen/review'), process_frontpage, {})

def process_frontpage(data, context, session):
    for p in data.xpath("//li[@class='article']"):
        context['name'] = p.xpath(".//a[@class='articleTitle']//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath(".//a[@class='articleTitle']/@href").string()
        context['category'] = p.xpath(".//a[@class='articleCategoryLabel']//text()[string-length(normalize-space(.))>0]").string()
        context['date'] = p.xpath(".//span[@class='date']/text()[string-length(normalize-space(.))>0]").string()
        context['excerpt'] = p.xpath(".//span[@class='articleIntroText']//text()[string-length(normalize-space(.))>0]").string()
        context['user'] = p.xpath(".//a[@class='authorLink']").first()
        category = p.xpath('.//span[@class="articleTypeLabel"]//text()[string-length(normalize-space(.))>0]').string()
        if context['name'] and context['url'] and category:
            if context['category'] in ['PC', 'Smartphone', 'Tablet','Overige elektronica'] or category in ['PC', 'Smartphone', 'Tablet','Overige elektronica']:
                session.queue(Request(context['url']), process_product, context)

    next = data.xpath('//a[contains(@class,"paginator__next")]//@href').string()
    if next:
        if '116' in next: next = next.replace('116','117')
        if '189' in next: next = next.replace('189','190')
        if '194' in next: next = next.replace('194','195')
        if '401' in next: next = next.replace('401','402')
        if '466' in next: next = next.replace('466','467')
        if '468' in next: next = next.replace('468','469')
        if '471' in next: next = next.replace('471','472')
        session.queue(Request(next), process_frontpage, {})

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']

    category = data.xpath('//div[@id="articleTagList"]//a//text()[not(regexp:test((.),"(Review|test)"))]').join('|')
    if category:
        product.category = category + ' | ' +context['category']
    else:
        product.category = context['category']

    if '"Articleid", "' in data.content:
        product.ssid = data.content.split('"Articleid", "')[1].split('"')[0]
    else:
        product.ssid = product.url + product.name

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid + ' review'
    review.type = 'pro'

    if '"datePublished": "' in data.content:
        pub_date = data.content.split('"datePublished": "')[1].split('"')[0]
        if 'T' in pub_date: pub_date=pub_date.split('T')[0]
        review.date = pub_date
    else:
        review.date = context['date']

    summary =  data.xpath('//node()[regexp:test(name(),"h\d")][regexp:test(descendant::text(),"(Conclus|conclus)")]/following::p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]').string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Conclusie"))

    for pros in data.xpath('//ul[contains(descendant::text(),"Pluspunten")]//li[@class="review__list--pro"]//text()'):
        p_value = pros.xpath('(.)').string()
        if p_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Pluspunten"))

    for cons in data.xpath('//ul[contains(descendant::text(),"Minpunten")]//li[@class="review__list--con"]//text()'):
        c_value = cons.xpath('(.)').string()
        if c_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Minpunten"))

    if 'ratingValue":' in data.content:
        grade = data.content.split('ratingValue":')[1].split('}')[0]
        if ',' in grade: grade = grade.replace(',','.')
        grade = float(grade) / 2.
        review.grades.append(Grade(name="SCORE", value = grade, worst = 0, best = 5, type = 'overall'))

    excerpt = context['excerpt']
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))

    user_data = context['user']
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('\/([^\/]+)$', user.profile_url)
        review.authors.append(user)

    if summary or excerpt:
        product.reviews.append(review)
        session.emit(product)
