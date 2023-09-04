from agent import *
from models.products import *

debug = True

import re


def run(context, session):
   session.queue(Request('http://www.photoaxe.com/category/cameras/'), process_revlist, {})


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "entry-title")]')
    for rev in revs:
        title = rev.xpath('a/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@class="next page-numbers"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, {})


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]

    product.category = 'Cameras'
    category = data.xpath('//span[@class="cat-links"]/a/text()').strings()
    if category:
        product.category = '|'.join(category).replace(' Reviews', '').replace('Other ', '')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time[contains(@class, "entry-date")]/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    conclusion = data.xpath('//div[@class="entry-content"]/h3/text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="entry-content"]/p[not(contains(., "Functions:") or contains(., "Technical Data:"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

############################################
    product.reviews.append(review)
    session.emit(product)
