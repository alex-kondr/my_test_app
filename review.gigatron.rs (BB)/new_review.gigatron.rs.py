#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def Request(url):
    r = agent.Request(url, force_charset='utf-8', use='curl')
    return r


def RequestProds(facets_path, page):
    url = 'https://gigatron.rs/api/vtex/plp-search?facetsPath={facets_path}&page={page}'.format(facets_path=facets_path, page=page)
    r = agent.Request(url, force_charset='utf-8', use='curl')
    return r


def RequestRevs(ssid, offset):
    url = 'https://gigatron.rs/api/vtex/product-reviews?productId={ssid}&from={offset}&to={to}'.format(ssid=ssid, offset=offset, to=offset + 9)
    r = agent.Request(url, force_charset='utf-8', use='curl')
    return r


def build_facets_path(cat_url):
    parts = [p for p in cat_url.replace('https://gigatron.vtexcommercestable.com.br/', '').replace('https://gigatron.rs/', '').strip('/').split('/') if p]
    facets = []
    for i, part in enumerate(parts):
        facets.append('category-' + str(i + 1) + '/' + part)
    return '/'.join(facets)


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://gigatron.rs/api/vtex/category-tree'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    try:
        cats = simplejson.loads(data.content)
    except:
        return

    for cat in cats:
        name = cat.get('name')

        cats1 = cat.get('children', [])
        if cats1:
            for cat1 in cats1:
                cat1_name = cat1.get('name')

                subcats = cat1.get('children', [])
                if subcats:
                    for subcat in subcats:
                        subcat_name = subcat.get('name')
                        url = subcat.get('url')

                        if subcat_name and url:
                            facets_path = build_facets_path(url)
                            if facets_path and not session.seen(facets_path):
                                session.queue(RequestProds(facets_path, 1), process_prodlist, dict(facets_path=facets_path, cat=name+'|'+cat1_name+'|'+subcat_name))
                else:
                    url = cat1.get('url')
                    if cat1_name and url:
                        facets_path = build_facets_path(url)
                        if facets_path and not session.seen(facets_path):
                            session.queue(RequestProds(facets_path, 1), process_prodlist, dict(facets_path=facets_path, cat=name+'|'+cat1_name))
        else:
            url = cat.get('url')
            if name and url:
                facets_path = build_facets_path(url)
                if facets_path and not session.seen(facets_path):
                    session.queue(RequestProds(facets_path, 1), process_prodlist, dict(facets_path=facets_path, cat=name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    try:
        prods_json = simplejson.loads(data.content).get('productRes', {})
    except:
        prods_json = {}

    prods = prods_json.get('products', [])
    for prod in prods:
        pr = dict()
        pr['name'] = prod.get('productName')
        pr['url'] = 'https://gigatron.rs/proizvod/' + prod.get('linkText')
        pr['ssid'] = prod.get('productId')
        pr['category'] = context['cat']

        try:
            pr['sku'] = prod.get('items', [{}])[0].get('itemId')
            pr['ean'] = prod.get('items', [{}])[0].get('referenceId', [{}])[0].get('Value')
        except:
            pass

        if pr['ssid'] and not session.seen(pr['ssid']):
            session.queue(Request(pr['url']), process_product, dict(product=pr))

    prods_cnt = context.get('prods_cnt', prods_json.get('recordsFiltered', 0))
    offset = context.get('offset', 0) + 24
    if offset < prods_cnt:
        next_page = context.get('page', 1) + 1
        session.queue(RequestProds(context['facets_path'], next_page), process_prodlist, dict(context, offset=offset, page=next_page, prods_cnt=prods_cnt))


def process_product(data: Response, context: dict[str, str], session: Session):
    try:
        prod_json = data.xpath('''//script[@type="application/ld+json" and contains(., '"@type":"Product"')]//text()''').string()
        prod_json = simplejson.loads(prod_json)
    except:
        return

    revs_cnt = prod_json.get('aggregateRating', {}).get('reviewCount', 0)
    if revs_cnt and int(revs_cnt) > 0:
        context['product']['manufacturer'] = prod_json.get('brand', {}).get('name')
        session.queue(RequestRevs(context['product']['ssid'], 0), process_reviews, dict(context, revs_cnt=int(revs_cnt)))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']
    product.sku = context['product'].get('sku')
    product.category = context['product']['category']
    product.manufacturer = context['product'].get('manufacturer')

    ean = context['product'].get('ean')
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('data', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev['id']

        date = rev.get('searchDate')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('reviewerName')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        for grade_key, grade_name in [('ratingPerformance', 'Performanse'), ('ratingQuality', 'Kvalitet'), ('ratingDesign', 'Dizajn')]:
            grade_val = rev.get(grade_key)
            if grade_val and float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

        is_verified_buyer = rev.get('verifiedPurchaser')
        if is_verified_buyer is True:
            review.add_property(type='is_verified_buyer', value=True)

        pros = rev.get('positiveText')
        if pros:
            pros = pros.strip(u' +-*.:;•,–')
            if len(pros) > 1:
                review.add_property(type='pros', value=pros)

        cons = rev.get('negativeText')
        if cons:
            cons = cons.strip(u' +-*.:;•,–')
            if len(cons) > 1:
                review.add_property(type='cons', value=cons)

        title = rev.get('title')
        excerpt = rev.get('text')
        if excerpt and len(excerpt.strip()) > 2:
            if title:
                review.title = title.strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

        if excerpt or pros or cons:
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    offset = context.get('offset', 0) + 10
    if offset < context['revs_cnt']:
        session.queue(RequestRevs(product.ssid, offset), process_reviews, dict(context, offset=offset))
