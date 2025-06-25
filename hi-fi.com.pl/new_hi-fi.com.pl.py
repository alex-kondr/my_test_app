from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.hi-fi.com.pl/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('(//li[a[contains(., "Testy")]])[1]/ul/li[not(contains(@class, "nested"))]/a[not(img)]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[a[contains(@class, "archive-post")]]')
    for rev in revs:
        title = rev.xpath('.//h3/text()').string()
        author = rev.xpath('.//p[contains(@class, "posts-author-name")]/text()').string()
        author_url = rev.xpath('.//a[contains(@class, "https://www.hi-fi.com.pl/author/")]/@href').string()
        url = rev.xpath('a[contains(@class, "archive-post")]/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, author=author, author_url=author_url, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if not next_url:
        next_url = data.xpath('//a[contains(@class, "next")]/@href').string()

    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Płyty testowe ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[@class="post-details" and div[@class="reading-time"]]/p/text()').string()
    if date:
        review.date = date.split('T')[0]

    author = context['author']
    author_url = context['author_url']
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//body/h2//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Konkluzja")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h3[contains(., "Konkluzja")])[1]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body/p[not(@style)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
