#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


def Request(url):
    r = agent.Request(url, force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.winnings.com.au/api/navbar/'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    cats_json = simplejson.loads(data.content)

    cats = cats_json.get('mainNav', {}).get('categories', [])
    for cat in cats:
        name = cat['title']

        cats1 = cat.get('subCategories', [])
        for cat1 in cats1:
            cat1_name = cat1['title']
            url = "https://www.winnings.com.au/api/category/" + cat1.get('uri', '').replace('/c/', '').replace('/', '%2F')

            subcats = cat1.get('subCategories')
            if subcats:
                for subcat in subcats:
                    subcat_name = subcat['title']
                    url = "https://www.winnings.com.au/api/category/" + subcat.get('uri', '').replace('/c/', '').replace('/', '%2F')
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name))
            else:
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name))



def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods_json = simplejson.loads(data.content)

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
    product.category = context['product']['category']
    product.url = context['product']['url']
    product.manufacturer = context['product'].get('brand')
    product.ssid = context['product']['mpn']

    product.add_property(type='id.manufacturer', value=product.ssid)


    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('allReviews', [])
    for rev in revs:
        syndicated = rev.get('isSyndicated')
        if syndicated and syndicated == True:
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev['id']
        review.title = rev.get('title')

        date = rev.get('submissionTime')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('userNickName')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        grades = rev.get('secondaryRatings', {})
        for name, grade in grades.items():
            value = grade.get('value')
            if name and value:
                review.grades.append(Grade(name=name, value=float(value), best=5.0))

        excerpt = rev.get('reviewText')
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            if not session.seen(review.ssid):
                product.reviews.append(review)

    if product.reviews:
        session.emit(product)
