from agent import *
from models.products import *
import re


def run(context, session):
    session.queue(Request('https://www.svenskgolf.se/tagg/test/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if not re.search(r'b.sta drivers|drivertest|j.rntest', title.lower()) :
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(': ')[-1].replace('Test!', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = data.xpath('//a[@rel="tag"]/text()').string()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[time]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//*[strong[contains(., "TOTALT:")]]/text()').string()
    if grade_overall:
        grade_val = grade_overall.split('/')[0].replace(u'\u2013', '').strip(' .+-*:')
        review.grades.append(Grade(type='overall', value=float(grade_val), best=50.0))

    grades =  data.xpath('//div[h4[contains(., "BETYG:")]]/p[normalize-space(.)]')
    for grade in grades:
        grade_name = grade.xpath('strong/text()').string().strip(' .+-*:').title()
        grade_val = grade.xpath('text()').string().strip(' .+-*:')
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('//p[strong[contains(., "PLUS:")]]/text()').string(multiple=True)
    if pros:
        review.add_property(type='pros', value=pros)

    cons = data.xpath('//p[strong[contains(., "MINUS:")]]/text()').string(multiple=True)
    if cons:
        review.add_property(type='cons', value=cons)

    summary = data.xpath('//div[contains(@class, "content-top") and header]/div[contains(@class, "text")]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "DRIVERTESTET")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[not(@class or @id)]//p[not(regexp:test(., "Pris|Loft") or @id or strong[regexp:test(., "TRÄFFKÄNSLA:|FÖRLÅTANDE:|VALMÖJLIGHET:|PLUS:|MINUS:|UTSEENDE:")])]//text()').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
