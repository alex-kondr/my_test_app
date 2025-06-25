from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://fotovilag.hu/content/index/cat/2', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div/a[@class="more"]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(url=url))

    next_url = data.xpath('//li[@title="kovetkezo"]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('(//div[@class="rb_content"]//h1)[1]//text()').string()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = 'Blog'

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//span[@class="mod-date"]/text()').string()

    summary = data.xpath('//h2//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('(//div[contains(@class, "content")]//p|//div[contains(@class, "content")]//blockquote)//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
