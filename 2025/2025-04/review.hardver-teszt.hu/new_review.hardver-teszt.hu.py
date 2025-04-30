from agent import *
from models.products import *


XCAT = ['Szolgátatás']


def run(context, session):
    session.queue(Request('http://www.hardver-teszt.hu/', use='curl'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[contains(@class, "tags")]//a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "archive")]//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat']

    review = Review()
    review.type = "pro"
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="entry-meta"]//span[contains(@class, "author")]/a/text()').string()
    author_url = data.xpath('//div[@class="entry-meta"]//span[contains(@class, "author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//div[contains(@class, "entry-content")]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
