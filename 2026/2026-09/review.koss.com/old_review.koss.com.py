#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://koss.com/collections/all', use='curl'), process_productlist, {})
    session.queue(Request('https://koss.com/collections/accessories', use='curl'), process_productlist, {})
    session.queue(Request('https://koss.com/collections/speakers', use='curl'), process_productlist, {})
    #all products
    #session.queue(Request('https://www.koss.com/ajax/infinite-scrolling/catalog/category/view/page/1/limit/999/requested-url/headphones'), process_productlist, {})
    #session.queue(Request('https://www.koss.com/ajax/infinite-scrolling/catalog/category/view/page/1/limit/999/requested-url/speakers'), process_productlist, {})
    #session.queue(Request('https://www.koss.com/ajax/infinite-scrolling/catalog/category/view/page/1/limit/999/requested-url/accessories'), process_productlist, {})


def process_productlist(data: Response, context: dict[str, str], session: Session):
    for cat in data.xpath('//div[@class="product-item"]//node()[regexp:test(name(),"h\d")]//a'):
        prUrl = cat.xpath('@href').string()
        prName = cat.xpath('descendant::text()').string()
        if prUrl and prName:
            session.queue(Request(prUrl, use='curl'), process_product, dict(context, prUrl=prUrl, prName=prName))

    next=data.xpath('//a[@data-pagination="next"]//@href').string()
    if next:
        session.queue(Request(next, use='curl'), process_productlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.category = data.xpath('//span[@class="product-detail-page"]//text()').join('|')
    product.name = context['prName']
    product.url = context['prUrl']

    pid = data.xpath('//div[@id="shopify-product-reviews"]//@data-id').string()
    if pid:
        product.ssid =  pid
        revUrl = 'https://productreviews.shopifycdn.com/proxy/v4/reviews?page=1&product_id=' + pid + '&shop=koss-stereophones.myshopify.com'
        session.queue(Request(revUrl, use='curl'), process_reviews, dict(context, product=product, pid=pid, base_url=revUrl))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    jstxt = data.content
    if jstxt[0:2]=='{}': jstxt = jstxt.replace('{}','', 1)

    json_data = simplejson.loads(jstxt)
    html_data = json_data['reviews']

    html_data= '<html><head></head><body>\n' + html_data + '\n</body></html>'
    data = data.parse_fragment(html_data)

    for rev in data.xpath('//div[@class="spr-review"]'):
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@id').string()
        review.title = rev.xpath('descendant::node()[@class="spr-review-header-title"]').string()

        revDate = rev.xpath('descendant::node()[@class="spr-review-header-byline"]/strong[2]//text()').string()
        if revDate:
            review.date = revDate

        revAuthor = rev.xpath('descendant::node()[@class="spr-review-header-byline"]/strong[1]//text()').string()
        if revAuthor:
            review.authors.append(Person(name=revAuthor, ssid=revAuthor))

        summary = rev.xpath('descendant::div[@class="spr-review-content"]//text()').string(multiple=True)
        if summary:
            review.add_property(type='summary', value=summary)

        revGradetxt = rev.xpath('descendant::i[@class="spr-icon spr-icon-star"]')
        if revGradetxt:
            revGrade = len(revGradetxt)
            review.grades.append(Grade(type='overall', name='Customer Rating', value=int(revGrade), best=5))

        product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    next = data.xpath('//a[contains(text(),"Next »")]//@data-page').string()
    if next:
        next = context['base_url'].replace('?page=1','?page=' + next)
        session.queue(Request(next, use='curl'), process_reviews, dict(context))