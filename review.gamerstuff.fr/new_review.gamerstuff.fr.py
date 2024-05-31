from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://gamerstuff.fr/category/tests/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="p-featured"]//a')
    for rev in revs:
        title = rev.xpath('@title').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.ssid = context['url'].split('/')[-2].replace('test-', '')
    product.category = 'Technologie'

    product.url = data.xpath('//a[@class="lnk-review-cdiscount"]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[@class="lnk-review-amazon"]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[@class="review-btn is-btn"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['url']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="meta-el meta-author"]/a/text()').string()
    author_url = data.xpath('//span[@class="meta-el meta-author"]/a/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="meta-score h4"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    summary = data.xpath('//div[@class="entry-content rbct clearfix"]//p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
