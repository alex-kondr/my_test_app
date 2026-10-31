#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ['View All', 'Retailer Exclusives']


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def Request(url):
    r = agent.Request(url, force_charset='utf-8', proxies=['rotating-us'])
    return r


def RequestRevs(url):
    r = agent.Request(url, force_charset='utf-8', proxies=['us'])
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request("https://bissell.com.au/"), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//li[a/@aria-label="Products"]//ul[not(@*[contains(name(), "data-nav-level")])]/li')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        if name not in XCAT:
            subcats = cat.xpath('ul/li/a')
            for subcat in subcats:
                subcat_name = subcat.xpath('text()').string()
                url = subcat.xpath('@href').string()

                if subcat_name not in XCAT:
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//product-card[@data-product-card]/div[contains(@class, "card__meta")]')
    for prod in prods:
        name = prod.xpath('h4/a/text()').string()
        ssid = prod.xpath('.//div/@data-oke-reviews-product-id').string()
        url = prod.xpath('h4/a/@href').string()

        revs_cnt = prod.xpath('.//span[contains(@class, "total-text")]/text()').string()
        if revs_cnt and int(revs_cnt.split()[0].lstrip('(')) > 0 and ssid and not session.seen(ssid):
            ssid = ssid.split('-')[-1]
            revs_url = "https://api.okendo.io/v1/stores/8a9b84b7-d620-404a-a611-264a38aa8c4b/products/shopify-{pid}/reviews?limit=10&orderBy=date%20desc".format(pid=ssid)
            session.queue(RequestRevs(revs_url), process_reviews, dict(context, name=name, url=url, ssid=ssid))

    next_url = data.xpath('//a[contains(@aria-label, "Next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = context['cat']
    product.manufacturer = "Bissell"

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev['reviewId']

        date = rev.get('dateCreated')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('reviewer', {}).get('displayName')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            if float(grade_overall) > 0:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        grades = rev.get('attributesWithRating', [{}])
        for grade in grades:
            name = grade.get('title')
            value = grade.get('value')
            if name and value and float(value) > 0:
                review.grades.append(Grade(name=name, value=float(value), best=5.0))

        is_verified = rev.get('reviewer', {}).get('isVerified')
        if is_verified is True:
            review.add_property(type='is_verified_buyer', value=True)

        is_recommended = rev.get('isRecommended')
        if is_recommended is True:
            review.add_property(type='is_recommended', value=True)
        elif is_recommended is False:
            review.add_property(type='is_recommended', value=False)

        hlp_yes = rev.get('helpfulCount')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('unhelpfulCount')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.get('title')
        excerpt = rev.get('body', '').strip()
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    next_link = revs_json.get('nextUrl')
    if next_link:
        next_url = "https://api.okendo.io/v1" + next_link
        session.queue(RequestRevs(next_url), process_reviews, dict(context))
