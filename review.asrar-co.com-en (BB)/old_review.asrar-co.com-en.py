#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import re


def is_string_arabic(s):
    return not bool(re.search(r'[\u0600-\u06FF]', s))


def Request(url):
    options = "-H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:80.0) Gecko/20100101 Firefox/80.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'Connection: keep-alive' -H 'Upgrade-Insecure-Requests: 1' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: Trailers' -H 'cookie: language=en-gb;'"
    r = agent.Request(url, use='curl', options='-s -L --insecure '+options, max_age=0, force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.asrar-co.com/index.php?route=product/catalog&limit=100'), process_productlist, {})


def process_productlist(data: Response, context: dict[str, str], session: Session):
    for prod in data.xpath("//div[@class='product-thumb']/div[@class='caption']/div[@class='name']/a"):
        url = prod.xpath('@href').string().replace('/ar/', '/en/')
        name = prod.xpath('text()').string()
        if url and name and not session.seen(url):
            session.queue(Request(url), process_product, dict(url=url, name=name))

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next + '&limit=100'), process_productlist, {})


def process_product(data: Response, context: dict[str, str], session: Session):
    rev_count = int(data.xpath("//div[@class='review-links']/a/text()").string().split('on ')[-1].split('reviews')[0])
    if rev_count == 0:
        return

    product = dict()
    product['name'] = data.xpath("//div[@class='title page-title']//text()").string()
    product['url'] = context['url']
    product['ssid'] = data.xpath("//input[@id='product-id']/@value").string()
    product['category'] = data.xpath("//ul[@class='breadcrumb']/li[position() < last()][position() > 1]/a/text()").join('|')
    product['mpn'] = data.xpath("//li[@class='product-mpn']/span/text()").string()

    session.queue(Request('https://www.asrar-co.com/index.php?route=product/product/review&product_id=' + product['ssid']), process_reviews, dict(product=product))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']
    product.category = context['product']['category']
    product.properties.append(ProductProperty(type='id.manufacturer', value=context['product']['mpn']))

    for rev in data.xpath("//table"):
        review = Review()
        review.type = 'user'
        review.url = context['product']['url']
        review.date = rev.xpath("tr[1]/td[2]/text()").string()

        author = rev.xpath(".//strong/text()").string()
        review.authors.append(Person(name=author, ssid=author))

        grade = int(rev.xpath("count(.//i[@class='fa fa-star fa-stack-2x'])"))
        if grade >= 0:
            review.grades.append(Grade(type='overall', value=grade, best=5))

        excerpt = rev.xpath(".//p//text()").string(multiple=True)
        if excerpt and not (is_string_arabic(excerpt) or is_string_arabic(author)):
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            review.ssid = review.digest()
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    next = data.xpath("//a[@class='next']/@href").string()
    if next:
        session.queue(Request(next), process_reviews, dict(context))
