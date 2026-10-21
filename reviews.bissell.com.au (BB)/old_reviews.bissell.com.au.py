#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


XCAT = ['View All']


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


def RequestRevs(url):
    r = agent.Request(url, force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request("https://bissell.com.au/"), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//li[@data-nav-item-level-1][a[contains(., "Products")]]//li[@class="subnav__item body-md"]')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        subcats = cat.xpath('ul/li/a')
        for subcat in subcats:
            url = subcat.xpath('@href').string()
            subcat_name = subcat.xpath('text()').string()

            if subcat_name not in XCAT:
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//product-card[@class="product-card"]')
    for prod in prods:
        name = prod.xpath('.//h4/a//text()').string()
        url = prod.xpath('.//h4/a/@href').string()
        ssid = prod.xpath('.//div/@data-oke-reviews-product-id').string()

        revs_cnt = prod.xpath('.//div[@class="oke-sr-count"]/span[@class="oke-sr-total-text"]/text()').string()
        if revs_cnt and int(revs_cnt.split()[0].lstrip('(')) > 0 and ssid and not session.seen(ssid):
            ssid = ssid.split('-')[-1]
            revs_url = "https://api.okendo.io/v1/stores/8a9b84b7-d620-404a-a611-264a38aa8c4b/products/shopify-{pid}/reviews?limit=10&orderBy=date%20desc".format(pid=ssid)
            session.queue(RequestRevs(revs_url), process_reviews, dict(context, name=name, url=url, ssid=ssid))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = "Bissell"
    product.ssid = context['ssid']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev['reviewId']
        review.title = rev.get('title')

        date = rev.get('dateCreated')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('reviewer')
        if author:
            author_name = author.get('displayName')
            review.authors.append(Person(name=author_name, ssid=author_name))

            is_verified = author.get('isVerified')
            if is_verified and is_verified == True:
                review.add_property(type='is_verified_buyer', value=True)

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        grades = rev.get('attributesWithRating', [{}])
        for grade in grades:
            name = grade.get('title')
            value = grade.get('value')
            if name and value:
                review.grades.append(Grade(name=name, value=float(value), best=5.0))

        is_recommended = rev.get('isRecommended')
        if is_recommended and is_recommended == True:
            review.add_property(value=True, type='is_recommended')
        elif is_recommended == False:
            review.add_property(value=False, type='is_recommended')

        hlp_yes = rev.get('helpfulCount')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('unhelpfulCount')
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        excerpt = rev.get('body', '').strip()
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)


    next_link = revs_json.get('nextUrl')
    if next_link:
        next_url = "https://api.okendo.io/v1" + next_link
        session.queue(RequestRevs(next_url), process_reviews, dict(context))
