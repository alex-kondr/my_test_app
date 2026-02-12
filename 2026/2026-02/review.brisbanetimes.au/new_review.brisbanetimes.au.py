from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.brisbanetimes.com.au/technology'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '')

    product.category = data.xpath('//h1/preceding-sibling::div[1]/a[not(regexp:test(., "Analysis|Technology"))]/text()').string()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content|//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@data-testid="author-bio"]/span/a[contains(@href, "https://www.brisbanetimes.com.au/by/")]/text()').string()
    author_url = data.xpath('//span[@data-testid="author-bio"]/span/a[contains(@href, "https://www.brisbanetimes.com.au/by/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//div[not(@role)]/p[not(@class or contains(., "Get news and reviews") or contains(., "Sign up here"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
