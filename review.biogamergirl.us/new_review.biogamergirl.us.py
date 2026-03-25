from agent import *
from models.products import *
import re
import time


SLEEP = 2


def run(context, session):
    session.queue(Request('http://www.biogamergirl.com/search/label/Video%20Game%20Reviews', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    time.sleep(SLEEP)

    revs = data.xpath('//h3[contains(@class, "post-title")]/a')
    for rev in revs:
        title = rev.xpath('.//text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@title="More posts"]/@href').string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_revlist, dict())


def process_review(data, context, session):
    time.sleep(SLEEP)

    product = Product()
    product.name = context['title'].split('Review: ')[-1].split(':')[0].split(' Review ')[0].split(' (')[0].replace(' Review', '').replace('Review -', '').replace('Oh...Sir!', '').strip()
    product.url = context['url']
    product.category = 'Tech'

    ssid = data.xpath('//div[contains(@id, "post-body")]/@id').string()
    if ssid:
        product.ssid = ssid.split('-')[-1]
    else:
        product.ssid = product.url.split('/')[-1].replace('.html', '').replace('review-', '')

    manufacturer = data.xpath('//strong[contains(text(), "Developer:")]/following-sibling::text()').string()
    if not manufacturer:
        manufacturer = data.xpath('//text()[contains(., "Developer:")]').string()

    if manufacturer:
        product.manufacturer = manufacturer.split('Developer:')[-1].split('|')[0].strip()

    platforme = data.xpath('//strong[contains(text(), "Reviewed on:")]/following-sibling::text()').string()
    if not platforme:
        platforme = data.xpath('//text()[contains(., "Reviewed on:")]').string()

    if platforme:
        product.category = 'Games|' + platforme.split('Reviewed on:')[-1].split('|')[0].strip()

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
        if not grade_overall:
            grade_overall = data.xpath('//strong[contains(text(), "SCORE:")]/text()').string()

        if grade_overall:
            grade_overall = grade_overall.replace('Score:', '').replace('SCORE:', '').split('/')[0].split('out')[0].replace('Review', '')
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
    if not conclusion:
        conclusion = data.xpath('//text()[contains(., "In conclusion, ")]/following-sibling::text()|(//text()[contains(., "In conclusion, ")]/following-sibling::a|//text()[contains(., "In conclusion, ")]/following-sibling::b|//text()[contains(., "In conclusion, ")]/following-sibling::i|//text()[contains(., "In conclusion, ")]/following-sibling::em|//text()[contains(., "In conclusion, ")]/following-sibling::strong)/text()').string(multiple=True)

    if conclusion:
        if summary:
            review.add_property(type='summary', value=summary)

        review.add_property(type='conclusion', value=conclusion)

    elif summary:
        review.add_property(type='conclusion', value=summary)

    excerpt = data.xpath('//h2[contains(., "Verdict")]/preceding-sibling::p[not(contains(., "Strengths:") or contains(., "Weaknesses:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(., "In conclusion, ")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//text()[contains(., "In conclusion, ")]/preceding-sibling::text()|(//text()[contains(., "In conclusion, ")]/preceding-sibling::a|//text()[contains(., "In conclusion, ")]/preceding-sibling::b|//text()[contains(., "In conclusion, ")]/preceding-sibling::i|strong)/text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@id, "post-body")]/p[not(regexp:test(., "Strengths:|Weaknesses:|Developer:|Publisher:|Score:") or preceding::p[regexp:test(., "Developer:|Publisher:")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@id, "post-body")]/div/p[not(regexp:test(., "Strengths:|Weaknesses:|Developer:|Publisher:|Score:|SCORE:") or preceding::p[regexp:test(., "Developer:|Publisher:")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//div[contains(@id, "post-body")]/a|//div[contains(@id, "post-body")]/b|//div[contains(@id, "post-body")]/i|//div[contains(@id, "post-body")]/strong|//div[contains(@id, "post-body")])/text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
