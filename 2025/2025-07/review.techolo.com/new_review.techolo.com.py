from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.techolo.com/search/label/Review', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(., "Load More")]/@data-load').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' - REVIEW', '').replace('Review: ', '').replace(' Review', '').replace(' Test', '').strip()
    product.ssid = context['url'].split('/')[-1].replace('.html', '').replace('-review', '')
    product.category = 'Tech'

    product.url = data.xpath('//span[contains(., "Product link")]/a/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(@href, "http://amzn.to/")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//div[@class="entry-meta"]/div[@class="align-left"]//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="entry-meta"]/div[@class="align-left"]//span[@class="author-name"]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//p[contains(., "Conclusion")]/following-sibling::p[not(.//em)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[contains(., "Conclusion")]/preceding-sibling::p[not(.//em)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "post-body")]/div[not(.//ul)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "post-body")]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
