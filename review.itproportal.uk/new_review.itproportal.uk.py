from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.itpro.com/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    page = int(data.xpath('//span[@class="active"]/text()').string())
    if page != context.get('page', 1):
        return

    revs = data.xpath('//a[@class="article-link"]')
    for rev in revs:
        title = rev.xpath('@aria-label').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = 'https://www.itpro.com/reviews/page/' + str(page + 1)
    session.queue(Request(next_url), process_revlist, dict(page=page + 1))


def process_review(data, context, session):
    product = Product()
    product.name = data.xpaht('//title/text()').string().replace('Review | ITPro', '').replace('review | ITPro', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@name="pub_date"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="parsely-author"]/@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))


