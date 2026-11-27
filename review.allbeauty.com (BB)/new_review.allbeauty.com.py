#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def RequestProds(page):
    url = 'https://www.allbeauty.com/products.json?limit=250&page=' + str(page)
    r = agent.Request(url, force_charset='utf-8', max_age=0)
    return r


def RequestRevs(pid, page):
    url = 'https://api.judge.me/reviews/reviews_for_widget?url=allbeauty-main.myshopify.com&shop_domain=allbeauty-main.myshopify.com&platform=shopify&page={page}&per_page=10&product_id={pid}'.format(page=page, pid=pid)
    r = agent.Request(url, force_charset='utf-8', max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(RequestProds(1), process_prodlist, dict())


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    try:
        prods = simplejson.loads(data.content).get('products', [])
    except:
        prods = []

    for prod in prods:
        handle = prod.get('handle')
        ssid = prod.get('id')
        if handle and ssid:
            pr = dict()
            pr['name'] = prod.get('title')
            pr['url'] = 'https://www.allbeauty.com/products/' + handle
            pr['ssid'] = str(ssid)
            pr['manufacturer'] = prod.get('vendor')

            pr['category'] = 'Beauty'
            cat = prod.get('product_type')
            if cat:
                pr['category'] = cat.replace(' > ', '|')

            try:
                pr['sku'] = str(prod.get('variants', [{}])[0].get('sku'))
            except:
                pr['sku'] = pr['ssid']

            if not session.seen(pr['ssid']):
                session.queue(RequestRevs(pr['ssid'], 1), process_reviews, dict(product=pr))

    if len(prods) == 250:
        page = context.get('page', 1) + 1
        session.queue(RequestProds(page), process_prodlist, dict(page=page))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']
    product.sku = context['product']['sku']
    product.category = context['product']['category']
    product.manufacturer = context['product'].get('manufacturer')

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('reviewer_name')
        if author and not rev.get('is_anonymous_reviewer'):
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('verified_buyer')
        if is_verified_buyer is True:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('thumb_up')
        if hlp_yes and int(hlp_yes):
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('thumb_down')
        if hlp_no and int(hlp_no):
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.get('title')
        body_html = rev.get('body_html')
        if body_html:
            excerpt = data.parse_fragment(body_html).xpath('//text()').string(multiple=True)
            if excerpt:
                if title and title.strip('.') != excerpt:
                    review.title = title
            else:
                excerpt = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            ssid = rev.get('uuid')
            if ssid:
                review.ssid = str(ssid)
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    page_cnt = context.get('page_cnt', revs_json.get('pagination', {}).get('total_pages', 1))
    page = context.get('page', 1) + 1
    if page <= page_cnt:
        session.queue(RequestRevs(product.ssid, page), process_reviews, dict(context, page_cnt=page_cnt, page=page))
