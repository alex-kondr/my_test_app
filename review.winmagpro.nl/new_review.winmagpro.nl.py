from agent import *
from models.products import *
import re


def run(context, session):
    session.queue(Request('https://www.winmagpro.nl/reviews', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[a and h2]')
    for rev in revs:
        title = rev.xpath('h2/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//li[@class="pager-next"]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' review: ')[0].replace('Getest: ', '').replace('Review: ', '').replace('Review ', '').replace(' Review', '').replace('REVIEW ', '').replace('Reviewoverzicht: ', '').replace('Preview: ', '').replace('REVIEW – ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('review-', '')
    product.category = data.xpath('//div[@class="field-section-select" and not(regexp:test(., "review|MKB Proof", "i"))]/a/text()').string() or 'Techniek'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[time[@class="date"]]/text()').string(multiple=True)
    if date:
        review.date = date.split(' - ')[0].split(', ')[-1].strip()

    grade_overall = data.xpath('//div[@class="content"]/img/@src').string()
    if grade_overall:
        grade_overall = re.search(r'editorschoice-\d{1,2}\.?\d?', grade_overall)
        if grade_overall:
            grade_overall = grade_overall.group().replace('editorschoice-', '').strip()
            if grade_overall and float(grade_overall) > 0:
                review.grades.append(Grade(type='grade_overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('(//h4[contains(., "Pluspunten")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    summary = data.xpath('//div[@class="field-lead-text rte-output"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Conclusie")]/following-sibling::p[not(contains(., "Meer info"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Conclusie")]/preceding-sibling::p//text()|//div[contains(@class, "field-body")]/text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "field-body")]/p[not(contains(., "Meer info"))]//text()|//div[contains(@class, "field-body")]/text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
