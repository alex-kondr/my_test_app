from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]

    session.queue(Request('http://www.gp.se/n%C3%B6je/film'), process_revlist, dict(cat='Film'))
    session.queue(Request('http://www.gp.se/om/Film'), process_revlist, dict(cat='Film'))
    session.queue(Request('http://www.gp.se/om/Filmrecension'), process_revlist, dict(cat='Film'))

    session.queue(Request('http://www.gp.se/n%C3%B6je/spel'), process_revlist, dict(cat='Spel'))
    session.queue(Request('http://www.gp.se/om/Spel'), process_revlist, dict(cat='Spel'))
    session.queue(Request('http://www.gp.se/om/Spelrecension'), process_revlist, dict(cat='Spel'))


def process_revlist(data, context, session):
    revs = data.xpath('//div[div/h2]/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, url=url))

    next_page = data.xpath('//button[contains(., "Nästa") and not(@disabled)]').string()
    if next_page:
        next_page = context.get('page', 1) + 1
        next_url = data.response_url.split('?')[0] + '?page={}'.format(next_page)
        session.queue(Request(next_url), process_revlist, dict(context, page=next_page))


def process_review(data, context, session):
    title = data.xpath('//h1//text()').string(multiple=True)

    product = Product()
    product.name = title
    product.url = context['url']
    product.ssid = product.url.split('.')[-1]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@data-testid="article-byline_top"]/span/a[@role="link"]/text()').string()
    author_url = data.xpath('//div[@data-testid="article-byline_top"]/span/a[@role="link"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//p[@data-testid="article-top_article-lead"]/span//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@data-testid="article-body_content"]/div/div/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
