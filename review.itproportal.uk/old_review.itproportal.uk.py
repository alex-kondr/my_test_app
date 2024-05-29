from agent import *
from models.products import *

import re
import datetime
import time

debug = True

def run(context, session):
   session.sessionbreakers = [SessionBreak(max_requests=20000)]
   session.queue(Request('http://www.itproportal.com/reviews/', use="curl"), process_revlist, dict())

def process_revlist(data, context, session):
    for rev in data.xpath('//div[contains(@class,"feature-block-item-wrapper")]'):
        url = rev.xpath('a//@href').string()
        title = rev.xpath('descendant::node()[@class="article-name"]//text()').string(multiple=True)
        if url and title:
            name = title
            bad_list2 = ['Tablet review:','Review:','reviewed',' review:',' review']
            for item in bad_list2:
                if item in name:
                    name = name.replace(item, '')

            session.queue(Request(url, use="curl"), process_product, dict(context, url=url, title=title, name=name))

    for rev in data.xpath('//div[contains(@class,"listingResult ")]'):
        url = rev.xpath('a//@href').string()
        title = rev.xpath('descendant::h3//text()').string(multiple=True)
        if url and title:
            name = title
            bad_list2 = ['Tablet review:','Review:','reviewed',' review:',' review']
            for item in bad_list2:
                if item in name:
                    name = name.replace(item, '')

            session.queue(Request(url, use="curl"), process_product, dict(context, url=url, title=title, name=name))

    next = data.xpath('//li[@class="pagination-numerical-list-item current-page"]/following-sibling::li[1]//a//@href').string()
    if next:
        """
        d = next.split('T')[0].split('-')
        t = next[11:].split('.')[0].split(':')
        print d, t

        d = datetime.date(int(d[0]),int(d[1]),int(d[2]))
        try:
            t = datetime.time(int(t[0]),int(t[1]),int(t[2])-1)
        except:
            t = datetime.time(int(t[0]),int(t[1]),int(t[2]))
        dt = datetime.datetime.combine(d, t)
        unix = int(time.mktime(dt.timetuple()))

        uri = 'http://www.itproportal.com/more/reviews/latest/' + str(unix) + '/'"""
        session.queue(Request(next, use="curl"), process_revlist, dict(context))

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.name
    product.category = 'Mobile | Gadgets'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = review.title

    pub_date = data.xpath('//time[@itemprop="datePublished"]//@datetime').string()
    if pub_date:
        if 'T' in pub_date: pub_date=pub_date.split('T')[0]
        review.date = pub_date
    else:
        review.date = 'unknown'

    author = data.xpath('//a[@rel="author"]//text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    score = data.xpath('//meta[@itemprop="ratingValue"]//@content').string(multiple=True)
    if score:
        if ',' in score: score = score.replace(',','.')
        review.grades.append(Grade(name='Rating', type='overall', value=float(score), best=5.0))

    # Summary
    summ_list = [
    '//node()[regexp:test(name(),"h\d")][regexp:test(descendant::text(),"(Verdict|Bottom line|Bottom Line)")]/following-sibling::p//text()',
    '//p[contains(descendant::text(), "Verdict")]/text()']

    for item in summ_list:
        summary=data.xpath(item).string(multiple=True)
        if summary:
            review.properties.append(ReviewProperty(type='summary',value=summary))
            break

    # Excerpt
    excerpt=data.xpath('//body[p]//p[not(@class)]//text()').string(multiple=True)
    if excerpt:
        if summary: excerpt = ''.join(excerpt.split(summary))
        review.properties.append(ReviewProperty(type='excerpt',value=excerpt[:1111]))

    # Pros
    pro = False
    for p in data.xpath('//node()[regexp:test(name(),"h\d")][regexp:test(descendant::text(),"(Pros|Good:)")]/following-sibling::ul[1]//li'):
        pros=p.xpath('descendant::text()').string(multiple=True)
        if pros:
            pro = pros
            review.properties.append(ReviewProperty(type='pros',value=pros))

    if not pro:
        pros=data.xpath('//node()[regexp:test(name(),"h\d")][regexp:test(descendant::text(),"(Pros|Good:)")]/following-sibling::p[1]//text()').string(multiple=True)
        if pros:
            pro = pros
            review.properties.append(ReviewProperty(type='pros',value=pros))

    if not pro:
        pros=data.xpath('//p//node()[regexp:test(descendant::text(),"(Pros|Good:)")]/following-sibling::text()[1]').string(multiple=True)
        if pros:
            pro = pros
            review.properties.append(ReviewProperty(type='pros',value=pros))

    # Cons
    con = False
    for c in data.xpath('//node()[regexp:test(name(),"h\d")][contains(descendant::text(),"Cons")]/following-sibling::ul[1]//li'):
        cons=c.xpath('descendant::text()').string(multiple=True)
        if cons:
            con = cons
            review.properties.append(ReviewProperty(type='cons',value=cons))

    if not con:
        cons=data.xpath('//node()[regexp:test(name(),"h\d")][regexp:test(descendant::text(),"(Cons|Bad:)")]/following-sibling::p[1]//text()').string(multiple=True)
        if cons:
            con = cons
            review.properties.append(ReviewProperty(type='cons',value=cons))

    if not con:
        cons=data.xpath('//node()[regexp:test(name(),"h\d")][regexp:test(descendant::text(),"(Cons|Bad:)")]/following-sibling::p[1]//text()').string(multiple=True)
        if cons:
            con = cons
            review.properties.append(ReviewProperty(type='cons',value=cons))

    if not con:
        cons=data.xpath('//p//node()[regexp:test(descendant::text(),"(Cons|Bad:)")]/following-sibling::text()[1]').string(multiple=True)
        if cons:
            con = cons
            review.properties.append(ReviewProperty(type='cons',value=cons))

    product.reviews.append(review)

    if product.reviews:
        session.emit(product)
