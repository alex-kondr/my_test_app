from agent import *
from models.products import *


XCAT = ['News']


def run(context, session):
    session.queue(Request('http://www.wir-testen-spiele.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="inner"]//li[contains(@class, "cat-item")]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = data.xpath('//article[@class="post"]/@id').string().replace('post-', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    conclusion = data.xpath('//h3[contains(., "Fazit")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Fazit")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry"]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
