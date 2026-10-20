#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


XCAT = ['BEST SELLERS', 'NEW ARRIVALS', 'meet matt(e) hughes®']


def Request(url):
    r = agent.Request(url, force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://thebalm.com/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//div[@class="megamenu__col"][a] | //div[@class="megamenu__col"][not(a)]/div')
    for cat in cats:
        name = cat.xpath('div[@class="megamenu__col-title"]/a//text()').string() or cat.xpath('a//text()').string()
        url = cat.xpath('a/@href').string()

        if name not in XCAT:
            subcats = cat.xpath('a[@class="site-nav__dropdown-link"]')
            if subcats:
                for subcat in subcats:
                    subcat_name = subcat.xpath('text()').string()
                    url = subcat.xpath('@href').string()

                    if subcat_name not in XCAT:
                        session.queue(Request(url), process_prodlist, dict(cat=name + "|" + subcat_name))
            else:
                session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//div[@class="grid-item grid-product"]')
    for prod in prods:
        name = prod.xpath('.//div[@class="grid-product__title"]//text()').string()
        url = prod.xpath('.//a[@class="grid-item__link"]/@href').string()
        ssid = prod.xpath('@data-product-id').string()
        if not session.seen(ssid):
            session.queue(Request(url), process_product, dict(context, name=name, url=url, ssid=ssid))

    # no next page


def process_product(data: Response, context: dict[str, str], session: Session):
    prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type": "Product"')]//text()''').string())

    pr = dict()
    pr['name'] = context['name']
    pr['url'] = context['url']
    pr['category'] = context['cat']
    pr['ssid'] = context['ssid']
    pr['sku'] = prod_json.get('sku')
    pr['ean'] = prod_json.get('gtin12')

    revs_cnt = data.xpath('//div[contains(@class, "ratingCount")]/span[not(@class)]//text()').string()
    if revs_cnt and int(revs_cnt.split()[0]) > 0:
        pid = data.xpath('//div/@data-oke-reviews-product-id').string()
        revs_url = "https://api.okendo.io/v1/stores/0267c601-87cc-41f1-a42b-8c579cee6e1a/products/" + pid + "/reviews?limit=100&orderBy=date%20desc"
        session.queue(Request(revs_url), process_reviews, dict(product=pr))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.category = context['product']['category']
    product.url = context['product']['url']
    product.manufacturer = 'theBalm'
    product.ssid = context['product']['ssid']
    product.sku = context['product'].get('sku')

    ean = context['product'].get('ean')
    if ean:
        product.add_property(type='id.ean', value=ean)

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

        author = rev.get('reviewer', {}).get('displayName')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        is_verified = rev.get('reviewer', {}).get('isVerified')
        if is_verified and is_verified == True:
            review.add_property(type='is_verified_buyer', value=True)

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_recommended = rev.get('isRecommended')
        if is_recommended and is_recommended == True:
            review.add_property(value=True, type='is_recommended')

        hlp_yes = rev.get('helpfulCount')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('unhelpfulCount')
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        excerpt = rev.get('body')
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    next_url = revs_json.get('nextUrl')
    if next_url:
        next_url = "https://api.okendo.io/v1" + next_url
        session.queue(Request(next_url), process_reviews, dict(context))
