#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.queue(Request('http://www.demonews.de/Spieletests/', use='curl'), process_revlist, {})


def process_revlist(data: Response, context: dict[str, str], session: Session):
    for rev in data.xpath("//h2/a"):
        title = rev.xpath("text()").string()
        url = rev.xpath("@href").string()
        if url and title:
            session.queue(Request(url, use='curl'), process_product, dict(url=url, title=title))

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next, use='curl'), process_revlist, context)


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = data.xpath("//a[@rel='tag' and regexp:test(@href,'game')]/text()").string()
    if not product.name:
        name = data.xpath("//h4[@class='mh-widget-title' and regexp:test(normalize-space(.),'Tests:')]//text()").string()
        if not name:
            if context['title'].startswith('Review:'):
                product.name = context['title'].replace('Review: ', '')
            else:
                product.name = context['title'].split(' Review:')[0]
        else:
            product.name = name.replace('Tests: ', '').strip()

    product.manufacturer = data.xpath("//a[@rel='tag' and regexp:test(@href,'companies')]/text()").string()
    product.url = context['url']
    product.category = data.xpath("//a[@rel='tag' and regexp:test(@href,'systems')]/text()").join('|') or 'Games'
    product.ssid = data.xpath("//article/@id").string().split('-')[-1]

    content = data.xpath("//article").first()
    if content:
        review = Review()
        review.type = 'pro'
        review.title = context['title']
        review.ssid = product.ssid
        review.url = product.url

        review.date = data.xpath("//time/@content").string().split('T')[0]
        if not review.date:
            review.date = data.xpath("//span[@class='entry-meta-date updated']//a/text()").string()

        author = data.xpath("//span[@class='entry-meta-author author vcard']//a").first()
        if author:
            name = author.xpath(".//text()").string(multiple=True)
            url = author.xpath("@href").string()
            review.authors.append(Person(name=name, ssid=url.split('/')[-2], profile_url=url))

        print(review.url)
        summary = data.xpath("//div[contains(@class, 'entry-content')]//p[strong]//text()").string(multiple=True)
        print 'XXX', summary
        if summary:
            review.properties.append(ReviewProperty(type='summary', value=summary))

        excerpt = data.xpath("//div[contains(@class, 'entry-content')]//p[normalize-space(text()) and following-sibling::node()[regexp:test(normalize-space(.),'^Fazit')]]//text()").string(multiple=True)
        if not excerpt:
            excerpt = data.xpath("//div[contains(@class, 'entry-content')]//p[normalize-space(text()) and following-sibling::h3[regexp:test(normalize-space(.),'Fazit')]]//text()").string(multiple=True)
        if not excerpt:
            excerpt = data.xpath("//div[contains(@class, 'entry-content')]//p[normalize-space(text())]//text()").string(multiple=True)
        if not excerpt:
            excerpt = data.xpath("//div[@class='old_content']//text()").string()
        print 'YYY', excerpt
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

        conclusion = data.xpath("//div[contains(@class, 'entry-content')]//p[normalize-space(text()) and preceding-sibling::node()[regexp:test(normalize-space(.),'^Fazit')]]//text()").string(multiple=True)
        if not conclusion:
            conclusion = data.xpath("//div[contains(@class, 'entry-content')]//p[normalize-space(text()) and preceding-sibling::h3[regexp:test(normalize-space(.),'Fazit')]]//text()").string(multiple=True)
        print 'ZZZ', conclusion
        if conclusion:
            review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

        for pro in data.xpath("//h3[regexp:test(normalize-space(.),'^Pro')]/following-sibling::ul[1]/li"):
            line = pro.xpath("descendant::text()").string(multiple=True)
            if line:
                review.properties.append(ReviewProperty(type='pros', value=line))

        for con in data.xpath("//h3[regexp:test(normalize-space(.),'^Contra')]/following-sibling::ul[1]/li"):
            line = con.xpath("descendant::text()").string(multiple=True)
            if line:
                review.properties.append(ReviewProperty(type='cons', value=line))

        if review.properties:
            product.reviews.append(review)

        grade = data.xpath("//img[regexp:test(@src,'demonews-logo.png')]/following-sibling::span/text()").string()
        if not grade:
            grade = data.xpath("//img[regexp:test(@src,'demonews-logo.png')]/following::span[1]/text()").string()
        if grade and grade.isdigit():
            review.grades.append(Grade(name="Bewertung", value = int(grade), worst = 0, best = 100, type = 'overall'))

    if product.reviews:
        session.emit(product)