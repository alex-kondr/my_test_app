from agent import *
from models.products import *
import re


CONCLUSION_WORDS = ['Conclusion', 'In the end, ', 'In conclusion, ', 'Overall, ', 'In summary, ']


def run(context, session):
    session.queue(Request('http://www.biogamergirl.com/search/label/Video%20Game%20Reviews', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "post-title")]/a')
    for rev in revs:
        title = rev.xpath('.//text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@title="More posts"]/@href').string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('Review: ')[-1].split(':')[0].split(' Review ')[0].split(' (')[0].replace(' Review', '').replace('Review -', '').replace('Oh...Sir!', '').strip()
    product.url = context['url']
    product.ssid = data.xpath('//div[contains(@id, "post-body")]/@id').string().split('-')[-1]
    product.category = 'Tech'
    product.manufacturer = data.xpath('//strong[contains(text(), "Developer:")]/following-sibling::text()[1]').string()

    platforme = data.xpath('//strong[contains(text(), "Reviewed on:")]/following-sibling::text()[1]').string()
    if platforme:
        product.category = 'Games|' + platforme

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    grade_overall = data.xpath('//b[contains(., "Score:") or regexp:test(., "\d+ out ")]//text()').string(multiple=True)
    if grade_overall:
        grade_val = re.search(r'\d+\.?\d?', grade_overall)
        grade_best = re.search(r'[\s/][510]+(?!\.)', grade_overall)
        if grade_val and grade_best:
            grade_val = float(grade_val.group())
            grade_best = float(grade_best.group().strip(' /'))
            review.grades.append(Grade(type='overall', value=grade_val, best=grade_best))

    if not grade_overall:
        grade_overall = data.xpath('//strong[contains(text(), "Score:")]/text()').string()
        if grade_overall:
            grade_overall = grade_overall.replace('Score:', '').split('/')[0]
            if grade_overall and float(grade_overall) > 0:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//p[contains(strong, "Strengths:")]/text()[normalize-space(.)]')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[contains(strong, "Weaknesses:")]/text()[normalize-space(.)]')
    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[contains(strong, "BioGamer Girl Review Verdict")]/following-sibling::p[1]//text()').string(multiple=True)

    conclusion = data.xpath('//u[contains(., "Conclusion")]/following-sibling::text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[preceding-sibling::h2[1][contains(., "Verdict")]]//text()').string(multiple=True)

    if conclusion:
        if summary:
            review.add_property(type='summary', value=summary)

        review.add_property(type='conclusion', value=conclusion)

    elif summary:
        review.add_property(type='conclusion', value=summary)

    excerpt = data.xpath('//h2[contains(., "Verdict")]/preceding-sibling::p[not(contains(., "Strengths:") or contains(., "Weaknesses:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@id, "post-body")]/p[not(regexp:test(., "Strengths:|Weaknesses:|Developer:|Publisher:|Score:") or preceding::p[regexp:test(., "Developer:|Publisher:")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
