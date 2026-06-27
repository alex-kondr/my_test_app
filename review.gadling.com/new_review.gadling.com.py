from agent import *
from models.products import *
import time
import random


def run(context, session):
    session.queue(Request('https://gadling.com/tag/travel-tech/', use='curl'), process_revlist, dict())


def process_revlist(data, context, session):
    time.sleep(random.uniform(2, 5))

    revs = data.xpath('//h2[@class="article-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if 'review' in title.lower():
            session.queue(Request(url, use='curl'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//div[@class="next"]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_revlist, dict())


def process_review(data, context, session):
    time.sleep(random.uniform(2, 5))

    if not data.xpath('//div[@class="article-content"]/p') and not context.get('repeat'):
        time.sleep(10)
        session.do(Request(data.response_url, use='curl', max_age=0), process_review, dict(context, repeat=True))
        return
    
    elif not data.xpath('//div[@class="article-content"]/p'):
        print data.content

    product = Product()
    product.name = context['title'].split(' Review: ')[-1].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('gadling-gear-review-', '')
    product.category = 'Gear'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="article-meta"]/a/text()').string()
    author_url = data.xpath('//div[@class="article-meta"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//div[@class="article-content"]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
