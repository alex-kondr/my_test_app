#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def process_revlist(data: Response, context: dict[str, str], session: Session):
    for rev in data.xpath("//h2[@itemprop='headline']//a"):
        url = rev.xpath("@href").string()
        title = rev.xpath("descendant::text()").string(multiple=True)
        if url and title:
            session.queue(Request(url), process_review, dict(url=url, title=title))

    next_url = data.xpath("//div[regexp:test(@class,'pagination-next')]//a/@href").string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    try:
        data.xpath("/")
    except:
        print('Page can\'t be processed')
        return
    
    product = Product()
    product.name = data.xpath("//h2[@class='cwp-item']//text()").string() or context['title']
    product.url = context['url']
    product.ssid = get_url_parameter(data.xpath("//link[@rel='shortlink']/@href").string(), 'p')
    product.category = 'E-Book Readers'

    content = data.xpath("//div[@itemprop='text']").first()
    if content:
        review = Review()
        review.type = 'pro'
        review.title = context['title']
        review.url = context['url']
        review.ssid = product.ssid
        review.date = re_search_once('^(.* \d{4})', data.xpath("//p[@class='entry-meta']//time/following-sibling::text()[1]").string())

        author = data.xpath("//p[@class='entry-meta']//a[@rel='author']").first()
        if author:
            name = author.xpath("descendant::text()").string(multiple=True)
            url = author.xpath("@href").string()
            if name and url:
                review.authors.append(Person(name=name, profile_url=url, ssid=name))

        excerpt = content.xpath("p[not(descendant::strong)][following-sibling::p[regexp:test(normalize-space(.),'Wrap up|My Thoughts','i')]]//text()").string(multiple=True)
        if not excerpt:
            excerpt = content.xpath("p[not(descendant::strong)][following-sibling::p[regexp:test(normalize-space(.),'Pros','i')]]//text()").string(multiple=True)
        if not excerpt:
            excerpt = content.xpath("p[not(descendant::strong)]//text()").string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

        conclusion = content.xpath("p[not(descendant::strong)][preceding-sibling::p[regexp:test(normalize-space(.),'Wrap up|My Thoughts','i')] and following-sibling::p[regexp:test(normalize-space(.),'Pros','i')]]//text()").string(multiple=True)
        if not conclusion:
            conclusion = content.xpath("p[not(descendant::strong)][preceding-sibling::p[regexp:test(normalize-space(.),'Wrap up|My Thoughts','i')]]//text()").string(multiple=True)
        if conclusion:
            review.add_property(type='conclusion', value=conclusion)

        pros = content.xpath("descendant::div[regexp:test(@class,'pros')]//ul/li")
        if not pros:
            pros = content.xpath("p[regexp:test(normalize-space(.),'Pros','i')]/following-sibling::ul[1]/li")
        for pro in pros:
            line = pro.xpath("descendant::text()").string(multiple=True)
            if line:
                review.add_property(type='pros', value=line)

        for pro in content.xpath("p[regexp:test(normalize-space(.),'^Pros$','i')]/following-sibling::p[1]//text()"):
            line = pro.xpath("self::text()").string(multiple=True)
            if line:
                review.add_property(type='pros', value=line)

        cons = content.xpath("descendant::div[regexp:test(@class,'cons')]//ul/li")
        if not cons:
            cons = content.xpath("p[regexp:test(normalize-space(.),'Cons','i')]/following-sibling::ul[1]/li")
        for con in cons:
            line = con.xpath("descendant::text()").string(multiple=True)
            if line:
                review.add_property(type='cons', value=line)

        for con in content.xpath("p[regexp:test(normalize-space(.),'^Cons$','i')]/following-sibling::p[1]//text()"):
            line = con.xpath("self::text()").string(multiple=True)
            if line:
                review.add_property(type='cons', value=line)

        valuetxt = content.xpath("descendant::div[@class='review-wu-grade-content']/div//span/text()").string(multiple=True)
        if not valuetxt:
            valuetxt = content.xpath("p[regexp:test(normalize-space(.),'Rating')]//text()").string(multiple=True)
        if valuetxt:
            value = re_search_once('(\d\.?\d?)', valuetxt)
            if value:
                review.grades.append(Grade(name='Rating', type='overall', value=float(value), best=10.0))

        for g in content.xpath("descendant::h3"):
            title = g.xpath("descendant::text()").string(multiple=True)
            valuetxt = g.xpath("following-sibling::span//span/text()").string(multiple=True)
            if title != 'Rating' and valuetxt:
                value = re_search_once('(\d\.?\d?)', valuetxt)
                review.grades.append(Grade(name=title, value=float(value), best=10.0))

        if excerpt:
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://goodereader.com/blog/category/reviews'), process_revlist, {})
