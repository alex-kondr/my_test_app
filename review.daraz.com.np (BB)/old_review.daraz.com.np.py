#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


def Request(url):
    options = "--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0' -H 'Accept-Language: en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br' -H 'Content-Type: application/json'"
    r = agent.Request(url, use='curl', proxies=['rotating-eu', 'rotating-us'], force_charset='utf-8', options='-s -L --insecure '+options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.daraz.com.np'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats1 = data.xpath('//ul[@data-spm="cate_1"]/li | //ul[@data-spm="cate_1"]/following-sibling::ul/li')
    for cat1 in cats1:
        name1 = cat1.xpath('span//a/span/text()').string()
        cat_id = cat1.xpath('span//a/@href').string().split('/')[-2]

        cats2 = cat1.xpath('ul//a')
        if cats2:
            for cat2 in cats2:
                name2 = cat2.xpath('span/text()').string()
                if name2 == name1:
                    continue

            cat_id = cat2.xpath('@href').string().split('/')[-2]
            url = 'https://www.daraz.com.np/{}/?ajax=true&page='.format(cat_id)
            session.queue(Request(url+'1'), process_prodlist, dict(cat=name1+'|'+name2, prods_url=url))

        else:
            url = 'https://www.daraz.com.np/{}/?ajax=true&page='.format(cat_id)
            session.queue(Request(url+'1'), process_prodlist, dict(cat=name1, prods_url=url))




def process_prodlist(data: Response, context: dict[str, str], session: Session):
    resp = simplejson.loads(data.content)

    prods = resp.get('mods', {}).get('listItems', [])
    for prod in prods:
        pr = dict()
        pr['name'] = prod.get('name')
        pr['url'] = 'https:' + prod.get('productUrl').split('?')[0]
        pr['category'] = context['cat']
        pr['sku'] = prod.get('sku')
        pr['ssid'] = prod.get('itemId')

        manufacturer = prod.get('brandName')
        if manufacturer and manufacturer.lower() != 'no brand':
            pr['manufacturer'] = manufacturer

        revs_cnt = prod.get('review')
        if revs_cnt and int(revs_cnt) > 0 and pr['ssid'] and not session.seen(pr['ssid']):
            url = 'https://my.daraz.com.np/pdp/review/getReviewList?itemId={}&pageSize=100'.format(pr['ssid'])
            session.queue(Request(url), process_reviews, dict(product=pr, revs_url=url))

    prods_cnt = context.get('prods_cnt', resp.get('mainInfo', {}).get('totalResults'))
    offset = context.get('offset', 0) + 40
    if prods_cnt and offset < int(prods_cnt):
        next_page = context.get('page', 1) + 1
        url = context['prods_url'] + str(next_page)
        session.queue(Request(url), process_prodlist, dict(context, prods_cnt=prods_cnt, offset=offset, page=next_page))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.ssid = context['product']['ssid']
    product.sku = context['product'].get('sku')
    product.category = context['product']['category']
    product.url = context['product']['url']
    product.manufacturer = context['product'].get('manufacturer')


    resp = simplejson.loads(data.content)
    if not resp:
        return

    revs = resp.get('model')
    if revs:
        revs = revs.get('items', [])
    else:
        return

    for rev in revs:
        review = Review()
        review.title = rev.get('reviewTitle')
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev['reviewRateId'])
        review.date = rev.get('reviewTime')

        author_name = rev.get('buyerName')
        author_ssid = rev.get('buyerId')
        author_email = rev.get('buyerEmail')
        if author_name and author_ssid and author_email:
            review.authors.append(Person(name=author_name, ssid=str(author_ssid), email=author_email))
        elif author_name and author_ssid:
            review.authors.append(Person(name=author_name, ssid=str(author_ssid)))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        is_verified = rev.get('isPurchased')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('upVotes')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('downVotes')
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('reviewContent')
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    revs_cnt = context.get('revs_cnt', resp.get('model', {}).get('paging', {}).get('totalItems'))
    offset = context.get('offset', 0) + 100
    if revs_cnt and offset < int(revs_cnt):
        next_page = context.get('page', 1) + 1
        url = context['revs_url'] + '&pageNo=' + str(next_page)
        session.queue(Request(url), process_prodlist, dict(context, revs_cnt=revs_cnt, offset=offset, page=next_page))
