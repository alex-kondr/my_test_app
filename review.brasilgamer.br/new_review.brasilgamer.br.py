from agent import *
from models.products import *


def run(context, session):
   session.queue(Request('http://www.brasilgamer.com.br/archive/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="link link--expand"]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[span[@aria-label="Próxima página"]]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('', '')
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = 'Tecnologia'

    review = Review()
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="author"]/a/text()').string()
    author_url = data.xpath('//span[@class="author"]/a/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//p[@class="strapline"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[strong[contains(., "Conclusão")]]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[strong[contains(., "Conclusão")]]/preceding-sibling::p[not(contains(., "Especificações técnicas:"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
