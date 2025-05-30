from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://gamecritics.com/tag/game-reviews/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "title")]//a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('SVG REVIEW:', '').replace('PREVIEW ', '').replace(' Review', '').replace(' review', '').strip(' –.')
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="entry-author"]/a/text()').string()
    author_url = data.xpath('//span[@class="entry-author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[contains(., "Rating")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = re.search(r'Rating.+\d+\.?\d?', grade_overall)
        if grade_overall:
            grade_overall = grade_overall.group(0).replace('Rating', '').split(':', 1)[-1].strip().split()[0].split('/')[0].replace(',', '.')
            if grade_overall and grade_overall[0].isdigit():
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    summary = data.xpath('//h2[@class="wp-block-heading"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//p[contains(., "Disclosures")]|//p[contains(., "Disclosures")]/following-sibling::p)//text()[not(contains(., ":"))]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="entry-content"]//p[count(preceding-sibling::hr) < 2 and not(b[regexp:test(., "HIGH|LOW|WTF|:")] or strong[regexp:test(., "HIGH|LOW|WTF|:")] or @class or @style or preceding-sibling::p[contains(., "Disclosures")] or contains(., "Disclosures"))]//text()').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
