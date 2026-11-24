#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ['Health Resource Center', 'Featured']


def remove_emoji(string):
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002500-\U00002BEF"  # chinese char
                               u"\U00002702-\U000027B0"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


def RequestProds(cat_id, page, offset):
    url = 'https://www.1mg.com/pwa-dweb-api/api/v5/category/{cat_id}?page={page}&per_page=20&component_offset={offset}'.format(cat_id=cat_id, page=page, offset=offset)
    r = Request(url, force_charset='utf-8')
    return r


def RequestRevs(ssid, page):
    url = 'https://www.1mg.com/pwa-dweb-api/api/v5/skus/{ssid}/reviews?page={page}'.format(ssid=ssid, page=page)
    r = Request(url, force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.1mg.com/pwa-dweb-api/api/v4/udp_tree', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    try:
        cats = simplejson.loads(data.content).get('data', {}).get('udp_tree', [])
    except:
        return

    for cat in cats:
        name = cat.get('name').strip()

        if name not in XCAT:
            subcats = cat.get('children', [])
            for subcat in subcats:
                subcat_name = subcat.get('name').strip()
                cat_id = subcat.get('id')

                if cat_id and name and subcat_name and not subcat_name.startswith('All '):
                    session.queue(RequestProds(cat_id, 0, 0), process_prodlist, dict(cat=name+'|'+subcat_name, cat_id=cat_id))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    try:
        prods_json = simplejson.loads(data.content).get('data', {})
    except:
        prods_json = {}

    prods = prods_json.get('widgets', [])
    for prod in prods:
        name = prod.get('name')
        ssid = prod.get('id')
        url = 'https://www.1mg.com' + prod.get('url')

        revs_cnt = prod.get('ratings') or {}
        if revs_cnt and int(revs_cnt.get('total_ratings', 0)) > 0 and not session.seen(ssid):
            session.queue(Request(url), process_product, dict(context, name=name, ssid=ssid, url=url))

    prods_cnt = context.get('prods_cnt', prods_json.get('meta', {}).get('total_record_count', 0))
    offset = context.get('offset', 0) + 20
    if offset < prods_cnt:
        next_page = context.get('page', 0) + 1
        session.queue(RequestProds(context['cat_id'], next_page, offset), process_prodlist, dict(context, offset=offset, prods_cnt=prods_cnt, page=next_page))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = dict()
    product['name'] = context['name']
    product['ssid'] = context['ssid']
    product['url'] = context['url']
    product['category'] = context['cat']

    try:
        prod_json = data.xpath('//script[contains(., "window.__INITIAL_STATE__")]/text()').string()
        prod_json = simplejson.loads(prod_json.split('window.__INITIAL_STATE__ = ')[-1].split('window.__STATUS_CODE__ =')[0])
    except:
        return

    product['manufacturer'] = prod_json.get('otcPageReducer', {}).get('staticData', {}).get('manufacturerInfo', {}).get('name')

    has_reviews = prod_json.get('otcPageReducer', {}).get('staticData', {}).get('hasReviews')
    if has_reviews is True:
        session.queue(RequestRevs(product['ssid'], 1), process_reviews, dict(product=product))



def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']
    product.sku = product.ssid
    product.category = context['product']['category']
    product.manufacturer = context['product']['manufacturer']

    try:
        revs_json = simplejson.loads(data.content).get('data', {}).get('ratings_and_reviews', {})
    except:
        revs_json = {}

    revs = revs_json.get('reviews', {}).get('values', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev['id'])

        date = rev.get('rating_created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('reviewer_name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('value')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev['is_verified']
        if is_verified is True:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev['review_description']
        if excerpt:
            excerpt = remove_emoji(excerpt).strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    revs_cnt = context.get('revs_cnt', revs_json.get('total_reviews', 0))
    offset = context.get('offset', 0) + 10
    if offset < revs_cnt:
        next_page = context.get('page', 1) + 1
        session.queue(RequestRevs(product.ssid, next_page), process_reviews, dict(context, page=next_page, revs_cnt=revs_cnt, offset=offset))
