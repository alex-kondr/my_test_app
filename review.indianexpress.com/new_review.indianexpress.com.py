from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('http://indianexpress.com/section/technology/tech-reviews/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' review:')[0].split(' Review:')[0].split(':')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].split('-')[-1]
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@href, "https://indianexpress.com/profile/author/")]//text()').string()
    author_url = data.xpath('//a[contains(@href, "https://indianexpress.com/profile/author/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="hide_rating"]//text()').string()
    if grade_overall:
        grade_overall = grade_overall.replace('Rating:', '').split('out of')[0].strip()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    summary = data.xpath('//h2[@itemprop="description"]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//div[@class="titled"]/p//text()').string(multiple=True)

    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[contains(@class, "content") or contains(@id, "content")]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
