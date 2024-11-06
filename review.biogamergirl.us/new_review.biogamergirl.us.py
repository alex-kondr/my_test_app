from agent import *
from models.products import *
import re


CONCLUSION_WORDS = ['In the end, ', 'In conclusion, ', 'Overall, ', 'In summary, ', 'Conclusion']


def run(context, session):
    session.queue(Request('http://www.biogamergirl.com/search/label/Video%20Game%20Reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "post-title")]/a')
    for rev in revs:
        title = rev.xpath('.//text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@title="More posts"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    excerpt = data.xpath('//div[contains(@id, "post-body")]/text()|(//div[contains(@id, "post-body")]/b|//div[contains(@id, "post-body")]/i)//text()').string(multiple=True)
    if not excerpt:
        return

    product = Product()
    product.name = context['title'].split('Review: ')[-1].split(':')[0].split(' Review ')[0].split(' (')[0].replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = data.xpath('//div[contains(@id, "post-body")]/@id').string().split('-')[-1]
    product.category = 'Tech'

    if " (" in context['title']:
        product.category = 'Games|' + context['title'].split(' (')[-1].replace('Review', '').strip(' ()')

    if 'Developer:' in excerpt:
        product.manufacturer = excerpt.split('Developer:')[-1].split('Publisher:')[0].strip()

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

    for word in CONCLUSION_WORDS:
        if word in excerpt:
            excerpt, conclusion = excerpt.rsplit(word, 1)
            conclusion = conclusion.split('Features:')[0].split('Game Information:')[0].split('Developer:')[0].split('Publisher:')[0].strip()
            review.add_property(type='conclusion', value=conclusion)
            break

    conclusion = data.xpath('//u[contains(., "Conclusion")]/following-sibling::text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

        excerpt = excerpt.replace(conclusion, '').strip()

    excerpt = excerpt.split('Features:')[0].split('Game Information:')[0].split('Developer:')[0].split('Publisher:')[0].strip()
    review.add_property(type='excerpt', value=excerpt)

    product.reviews.append(review)

    session.emit(product)
