#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


def Request(url):
    r = agent.Request(url, force_charset="utf-8")
    return r


def RequestProds(channel_id, page_id, cat_id, domain_id, page):
    url = "https://www.nordicfeel.se/api/productFilter/jsonWithProducts?page=" + str(page)
    options = """-H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0' -H 'Accept: */*' -H 'Accept-Language: en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Content-Type: application/json' -H 'litium-request-context: {"channelSystemId":\"""" + channel_id + """","currentPageSystemId":\"""" + page_id + """","productCategorySystemId":\"""" + cat_id + """","domainNameSystemId":\"""" + domain_id + """"}'"""
    r = agent.Request(url, use='curl', force_charset="utf-8", options='-s -L --insecure '+options, max_age=0)
    return r


def RequestRevs(channel_id, page_id, cat_id, domain_id, pid, page):
    url = "https://www.nordicfeel.se/json/productreviews/fetch?baseProductId=" + pid + "&page=" + str(page)
    options = """--compressed -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0' -H 'Accept: */*' -H 'Accept-Language: en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Content-Type: application/json' -H 'litium-request-context: {"channelSystemId":\"""" + channel_id + """","currentPageSystemId":\"""" + page_id + """","productCategorySystemId":\"""" + cat_id + """","domainNameSystemId":\"""" + domain_id + """"}'"""
    r = agent.Request(url, use='curl', force_charset="utf-8", proxies=['rotating-eu'], options='-s -L --insecure '+options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.nordicfeel.se/json/navigation/fetchMenu?fullMenu=true'), process_cats_json, dict())


def process_cats_json(data: Response, context: dict[str, str], session: Session):
    cats_json = simplejson.loads(data.content)

    cats = cats_json.get('contentLinks', [])
    for cat in cats:

        if cat['type'] == 'Category':
            name = cat['name']
            url = 'https://www.nordicfeel.se' + cat['url']

            cats1 = cat.get('links')
            if cats1:
                for cat1 in cats1:
                    cat1_name = cat1['name']
                    url = 'https://www.nordicfeel.se' + cat1['url']

                    subcats = cat1.get('links')
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat['name']
                            url = 'https://www.nordicfeel.se' + subcat['url']
                            session.queue(Request(url), process_cat_id, dict(cat=name + "|" + cat1_name + "|" + subcat_name))

                    else:
                        session.queue(Request(url), process_cat_id, dict(cat=name + "|" + cat1_name))

            else:
                session.queue(Request(url), process_cat_id, dict(cat=name))


def process_cat_id(data: Response, context: dict[str, str], session: Session):
    cat_info = data.xpath('''//script[contains(., '"requestContext": ')]//text()''').string()
    if cat_info:
        channel_id = cat_info.split('"channelSystemId": "')[-1].split('"')[0]
        page_id = cat_info.split('"currentPageSystemId": "')[-1].split('"')[0]
        cat_id = cat_info.split('"productCategorySystemId": "')[-1].split('"')[0]
        domain_id = cat_info.split('"domainNameSystemId": "')[-1].split('"')[0]
        if channel_id and page_id and cat_id and domain_id:
            session.queue(RequestProds(channel_id, page_id, cat_id, domain_id, 1), process_prodlist, dict(context, channel_id=channel_id, page_id=page_id, cat_id=cat_id, domain_id=domain_id))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods_json = simplejson.loads(data.content)

    prods = prods_json.get('products', [])
    for prod in prods:
        pr = dict()
        pr['name'] = prod.get('name')
        pr['category'] = context['cat']
        pr['url'] = 'https://www.nordicfeel.se' + prod.get('url', '')
        pr['manufacturer'] = prod.get('brand')
        pr['ssid'] = prod.get('id')
        pr['ean'] = prod.get('ean')

        pid = prod.get('baseProductId')
        revs_cnt = prod.get('rateAndReviewItemModel', {}).get('numberOfRating')
        if revs_cnt and int(revs_cnt) > 0 and pid and not session.seen(pid):
            session.queue(RequestRevs(context['channel_id'], context['page_id'], context['cat_id'], context['domain_id'], pid, 1), process_reviews, dict(context, product=pr, pid=pid))

    prods_cnt = context.get('prods_cnt', prods_json.get('pagination', {}).get('totalCount'))
    offset = context.get('offset', 0) + 48
    if prods_cnt and int(prods_cnt) > offset:
        next_page = context.get('page', 1) + 1
        session.queue(RequestProds(context['channel_id'], context['page_id'], context['cat_id'], context['domain_id'], next_page), process_prodlist, dict(context, prods_cnt=prods_cnt, offset=offset, page=next_page))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.category = context['product']['category']
    product.url = context['product']['url']
    product.manufacturer = context['product'].get('manufacturer')
    product.ssid = context['product']['ssid']

    ean = context['product'].get('ean')
    if ean:
        product.add_property(type='id.ean', value=ean)


    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('productReviews', [])
    for rev in revs:

        lng = rev.get('language')
        if lng and lng != 'sv':
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev['id']
        review.title = rev.get('_source', {}).get('review_title')

        date = rev.get('createdAt')
        if date:
            review.date = date.split()[0]

        author = rev.get('consumer', {}).get('displayName')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('stars')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('content')
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            if not session.seen(review.ssid):
                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    revs_cnt = context.get('revs_cnt', revs_json.get('pagination', {}).get('totalCount'))
    offset = context.get('offset', 0) + 10
    if revs_cnt and int(revs_cnt) > offset:
        next_page = context.get('page', 1) + 1
        session.queue(RequestRevs(context['channel_id'], context['page_id'], context['cat_id'], context['domain_id'], context['pid'], next_page), process_reviews, dict(context, revs_cnt=revs_cnt, offset=offset, page=next_page))
