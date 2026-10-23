#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def Request(url):
    r = agent.Request(url, force_charset='utf-8', proxies=['eu'])
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.winnings.com.au/api/navbar/'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    try:
        cats_json = simplejson.loads(data.content)
    except:
        return

    cats = cats_json.get('mainNav', {}).get('categories', [])
    for cat in cats:
        name = cat['title']

        cats1 = cat.get('subCategories', [])
        for cat1 in cats1:
            cat1_name = cat1['title']

            subcats = cat1.get('subCategories')
            if subcats:
                for subcat in subcats:
                    subcat_name = subcat['title']
                    url = "https://www.winnings.com.au/api/category/" + subcat.get('uri', '').replace('/c/', '').replace('/', '%2F')
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name))
            else:
                url = "https://www.winnings.com.au/api/category/" + cat1.get('uri', '').replace('/c/', '').replace('/', '%2F')
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name))



def process_prodlist(data: Response, context: dict[str, str], session: Session):
    try:
        prods_json = simplejson.loads(data.content)
    except:
        return

    prods = prods_json.get('products', [])
    for prod in prods:
        pr = dict()
        pr['name'] = prod.get('title')
        pr['url'] = "https://www.winnings.com.au/p" + prod.get('uri', '')
        pr['category'] = context['cat']
        pr['brand'] = prod.get('brand')
        pr['mpn'] = prod.get('productCode')

        revs = prod.get('reviews')
        if revs and pr['mpn'] and not session.seen(pr['mpn']):
            revs_url = "https://www.winnings.com.au/api/review/" + pr['mpn']
            session.queue(Request(revs_url), process_reviews, dict(product=pr))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = context['product']['mpn']
    product.category = context['product']['category']
    product.manufacturer = context['product']['brand']

    product.add_property(type='id.manufacturer', value=product.ssid)

    try:
        revs_json = simplejson.loads(data.content)
    except:
        return

    revs = revs_json.get('allReviews', [])
    for rev in revs:
        if rev.get('isSyndicated') is True:
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev['id']

        date = rev.get('submissionTime')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('userNickName')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('ratingRange')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        grades = rev.get('secondaryRatings', {})
        for name, grade in grades.items():
            value = grade.get('value')
            if name and value:
                review.grades.append(Grade(name=name, value=float(value), best=5.0))

        title = rev.get('title')
        excerpt = rev.get('reviewText')
        if excerpt:
            if title != excerpt:
                review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            if not session.seen(review.ssid):
                product.reviews.append(review)

    if product.reviews:
        session.emit(product)
