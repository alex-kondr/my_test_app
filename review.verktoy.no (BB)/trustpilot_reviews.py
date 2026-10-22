#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson, HTMLParser

h = HTMLParser.HTMLParser()

import _proxies_config
reload(_proxies_config)
PROXIES = _proxies_config.us_rotating_proxies

PERPAGE = 100

def process_reviews_json_request_TP(data, context, session):
    url = 'https://widget.trustpilot.com/trustbox-data/%s?businessUnitId=%s&locale=%s&sku=%s&reviewsPerPage=%s' % (context['app_key'], context['businessunit'], context['locale'], context['product']['sku'], context.get('perpage', PERPAGE))
    if context.get('language'):
        url += '&reviewLanguages=%s'%(context['language'])
    session.queue(Request(url), process_reviews, dict(context))

def process_reviews(data, context, session):
    product = Product()
    product.name = context['product']['name']
    product.manufacturer = context['product']['manufacturer']
    product.url = context['product']['url']
    product.category = context['product']['category']
    product.ssid = context['product']['ssid']
    product.sku = context['product']['sku']

    mpn = context['product'].get('id.manufacturer')
    if mpn:
        product.properties.append(ProductProperty(name="MPN", type="id.manufacturer", value=mpn))

    ean = context['product'].get('id.ean')
    if ean:
        product.properties.append(ProductProperty(name="EAN", type="id.ean", value=ean))

    sku = context['product'].get('id.sku')
    if sku:
        product.properties.append(ProductProperty(name="SKU", type="id.sku", value=sku))

    resp = simplejson.loads(data.content)

    try:
        verified_revs = resp['productReviews']['reviews']
        revs = resp['importedProductReviews']['productReviews']
        verified_revs.extend(revs)
    except:
        return

    cnt = 0
    for rev in verified_revs:
        cnt += 1
        review = Review()
        review.type = 'user'
        review.url = product.url
        
        source = rev.get('source', None)
        if source:
            print 'zzz', cnt, 'syndicated'
            continue
        
        review.date = rev['createdAt'].split('T')[0]
        author = rev['consumer']['displayName']
        review.authors.append(Person(name=h.unescape(author), ssid=h.unescape(author)))
        
        excerpt = rev['content']
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=h.unescape(excerpt)))

        grade_overall = rev['stars']
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        if rev.get('attributes', {}):
            for k in rev['attributes'].keys():
                value = rev['attributes'][k]
                if value:
                    review.grades.append(Grade(name=k, value=float(value), best=5.0))
        
        verified = None
        review.ssid = rev.get('id')
        if review.ssid:
            verified = True
            review.add_property(type='is_verified_buyer', value=True)
        if not review.ssid:
            review.ssid = review.digest()

        if not(context.get('verified_only')):
            product.reviews.append(review)
        elif verified and context.get('verified_only'):
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    next_url = resp['importedProductReviews']['links']['nextPage']
    if not(next_url):
        next_url = resp['productReviews']['links']['nextPage']
    if next_url:
        next_url = data.resolve_url(next_url)
        session.queue(Request(next_url), process_reviews, dict(context))

