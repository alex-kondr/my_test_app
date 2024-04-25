# -*- coding: utf8 -*-
from agent import *
from models.products import *
import re
import base64

# adapted from https://github.com/Shani-08/ShaniXBMCWork2/blob/master/plugin.video.live.streamspro/sucuri_cookie.py

SU_COOKIE = ""

import agent
def request(url, max_age=0):
   r = agent.Request(url, ignore_errors=True, max_age=max_age)
   r.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
   r.add_header('Cookie', SU_COOKIE)
   print "SUC:", SU_COOKIE
   return r
Request = request


def _get_sucuri_cookie(html):
    print html
    if 'sucuri_cloudproxy_js' in html:
        match = re.search("S\s*=\s*'([^']+)", html)
        if match:
            print 'match:',match
            s = base64.b64decode(match.group(1))
            s = s.replace(' ', '')
            s = re.sub('String\.fromCharCode\(([^)]+)\)', r'chr(\1)', s)
            s = re.sub('\.slice\((\d+),(\d+)\)', r'[\1:\2]', s)
            s = re.sub('\.charAt\(([^)]+)\)', r'[\1]', s)
            s = re.sub('\.substr\((\d+),(\d+)\)', r'[\1:\1+\2]', s)
            s = re.sub(';location.reload\(\);', '', s)
            s = re.sub(r'\n', '', s)
            s = re.sub(r'document\.cookie', 'cookie', s)
            try:
                print 's:',s
                cookie = ''
                exec(s)
                match = re.match('([^=]+)=(.*)', cookie)
                if match:
                    return {match.group(1): match.group(2)}
            except Exception as e:
                print 'Exception during sucuri js: %s' % (e)


def run(context, session):
   session.sessionbreakers = [SessionBreak(max_requests=20000)]
   session.queue(agent.Request('http://www.pcquest.com/reviews/', max_age=0, use="curl"), process_first_page, {'url': 'http://www.pcquest.com/reviews/'})


def process_first_page(data, context, session):
    global SU_COOKIE
    print 'data:', data.content
    su_c = _get_sucuri_cookie(data.content).items()[0]
    SU_COOKIE = su_c[0] + "=" + su_c[1].split(';')[0]
    session.queue(Request(context['url']), process_category, dict())


def process_category(data, context, session):
    # print data.content
    for link in data.xpath('//div[contains(@class,"item-content")]//h3//a'):
        url=link.xpath('@href').string()
        name=link.xpath('text()').string()
        category=link.xpath('../../div[@class="content-category"]//a[not(regexp:test(@href,"(news|reports|features|advice)"))]//text()').join(' | ')
        if url and name and category:# and 'review' in url:
            bad_list = [' review: ']
            for item in bad_list:
                if item in name:
                    namex = name.split(item)[0]
                    if len(namex) == 0:
                        name = name.split(item)[1]
                    else:
                        name = namex
                    break

            bad_list2 = [' review',': Review',' Review','First look:','']
            for item in bad_list2:
                if item in name:
                    name = name.replace(item, '')

            category = category.replace('Reviews', 'unknown')

            session.queue(Request(url),process_product,dict(context,url=url,name=name, category = category))

    # Next page
    next=data.xpath('//div[@class="pagination"]//a[@class="next page-numbers"]//@href').string()
    if next:
        session.queue(Request(next), process_category, dict(context))


def process_product(data, context, session):
    product=Product()
    product.name=context['name']
    product.url=context['url']
    product.ssid=product.name + ' ' + product.url
    product.category=context['category']
    product.manufacturer=''

    review=Review()
    review.product=product.name
    review.url=product.url
    review.type='pro'
    review.ssid=product.ssid

    # Publish date
    pub_date=data.xpath('//meta[@name="shareaholic:article_published_time"]//@content').string(multiple=True)
    if pub_date:
        review.date=pub_date[:-15]
    else:
        review.date='unknown'

    # Author
    author=data.xpath('//meta[@name="shareaholic:article_author_name"]//@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))
    else:
        review.authors.append(Person(name='pcquest.com', ssid='pcquest.com'))

    # Grades
    overall=data.xpath('//div[@class="quality-ratings"]//li[@class="pcq"]//img//@src').string()
    if overall and 'Please+Choose' not in overall:
        score = overall.split('rating/')[1][:-4]
        if '_h' in score:
            score = float(score[:-2]) + 0.5

        review.grades.append(Grade(name='Overall Rating', type='overall', value=float(score), best=5))

    for sc in data.xpath('//div[@class="quality-ratings"]//li[not(@class="pcq")]'):
        value=sc.xpath('h4//text()').string()
        score=sc.xpath('img//@src').string()
        if value and score and 'Please+Choose' not in score:
            score = score.split('rating/')[1][:-4]
            if '_h' in score:
                score = float(score[:-2]) + 0.5

            review.grades.append(Grade(name=value, value=float(score), best=5))

    for g in data.xpath('//div[@class="review-item-line"]'):
        value=g.xpath('div//span/@style').string()
        name=g.xpath('strong//text()').string()
        if value and name:
            value= float(value.replace('width: ','')[:-2]) / 10.
            if 'Overall' in name:
                review.grades.append(Grade(name='Overall Rating', type='overall', value=float(value), best=10))
            else:
                review.grades.append(Grade(name=name, value=float(value), best=10))

    # Summary
    summary=data.xpath('//div[@class="left-content left"]/div/p/text()').string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type='summary',value=summary))

    # Conclusion
    conclusion = data.xpath('//div[@class="content-new"]//p//span[contains(text(), "Bottomline:")]//following-sibling::text()').string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    # Pros
    pros=data.xpath('//div[@class="content-new"]//p//span[contains(text(), "Pros:")]//following-sibling::text()').string(multiple=True)
    if pros:
        review.properties.append(ReviewProperty(type='pros',value=pros))

    # Cons
    cons=data.xpath('//div[@class="content-new"]//p//span[contains(text(), "Cons:")]//following-sibling::text()').string(multiple=True)
    if cons:
        review.properties.append(ReviewProperty(type='cons',value=cons))

    product.reviews.append(review)

    if product.reviews and summary:
        session.emit(product)
