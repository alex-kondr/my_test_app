#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ['Marken', 'Angebote & B-Ware|Aktuelle Deals', 'Ratgeber', 'Blog']


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
    r = agent.Request(url, proxies=['rotating-eu', 'rotating-us'], use='curl', force_charset='utf-8')
    return r


def RequestRevs(ssid, page):
    url = 'https://cdn.judge.me/reviews/reviews_for_widget?product_id={}&page={}&shop_domain=beamer-discount.myshopify.com&platform=shopify'.format(ssid, page)
    r = agent.Request(url, proxies=['rotating-eu', 'rotating-us'], use='curl', force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.beamer-discount.de/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//nav[@aria-label="Primär"]/ul/li')
    for cat in cats:
        name = cat.xpath('div[contains(@class, "row")]/a/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('div/div/ul/li')
            for cat1 in cats1:
                cat1_name = cat1.xpath('div[contains(@class, "item")]/a/text()').string()

                if cat1_name not in XCAT:
                    subcats = cat1.xpath('div/ul/li/a')
                    for subcat in subcats:
                        subcat_name = subcat.xpath('.//text()').string(multiple=True)
                        url = subcat.xpath('@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//product-card')
    for prod in prods:
        name = prod.xpath('.//span[contains(@class, "card-title-main")]/text()').string()
        ssid = prod.xpath('@data-product-id').string()
        url = prod.xpath('.//a[contains(@class, "prod-link")]/@href').string().split('?')[0]

        revs_cnt = prod.xpath('.//div[contains(@class, "rating__count")]/text()').string()
        if revs_cnt:
            revs_cnt = int(revs_cnt.strip('( )'))
            if revs_cnt > 0:
                session.queue(Request(url), process_product, dict(context, name=name, ssid=ssid, url=url, revs_cnt=revs_cnt))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    pr = dict()
    pr['name'] = context['name']
    pr['url'] = context['url']
    pr['ssid'] = context['ssid']
    pr['sku'] = data.xpath('//span[@class="product-sku__value"]/text()').string()
    pr['category'] = context['cat']
    pr['manufacturer'] = data.xpath('//li[contains(div/text(), "Marke")]/div[contains(@class, "value")]//text()').string()
    pr['mpn'] = data.xpath('//li[contains(div/text(), "Hersteller-Artikelnumme")]/div[contains(@class, "value")]//text()').string(multiple=True)
    pr['ean'] = data.xpath('//li[contains(div/text(), "EAN")]/div[contains(@class, "value")]//text()').string()

    session.queue(RequestRevs(pr['ssid'], 1), process_reviews, dict(context, product=pr))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']
    product.sku = context['product']['sku']
    product.category = context['product']['category']
    product.manufacturer = context['product']['manufacturer']

    mpn = context['product'].get('mpn')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = context['product'].get('ean')
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    try:
        revs = simplejson.loads(data.content).get('reviews', [])
    except:
        revs = []

    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('uuid')

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('reviewer_name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        if rev.get('verified_buyer'):
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('thumb_up')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('thumb_down')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.get('title')
        excerpt = rev.get('body_html')
        if excerpt:
            excerpt = data.parse_fragment(excerpt).xpath('.//text()').string(multiple=True)

        if excerpt:
            review.title = title
        elif title:
            excerpt = title

        if excerpt and len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt)

            if not review.ssid:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        session.queue(RequestRevs(product.ssid, next_page), process_reviews, dict(context, page=next_page, offset=offset))
