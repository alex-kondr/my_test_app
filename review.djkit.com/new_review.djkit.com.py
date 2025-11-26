#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


XCAT = ['Black Friday', 'Top Brands', 'Best Sellers', 'Shop by Brand', 'To Brands', 'Best sellers', 'Sale items', 'More', 'Brands']


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


def RequestRevs(pid, page):
    url = 'https://api.judge.me/reviews/reviews_for_widget?url=b4f450-9b.myshopify.com&shop_domain=b4f450-9b.myshopify.com&platform=shopify&page={page}&per_page=5&product_id={pid}'.format(pid=pid, page=page)
    r = agent.Request(url, proxies=['eu'])
    return r


def Request(url):
    r = agent.Request(url, proxies=['eu'])
    return r


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request("https://www.djkit.com"), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[@data-type="horizontal-nav"]/li')

    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('ul/li/ul/li')

            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a/text()').string()

                if 'Shop all ' not in sub_name and 'Used ' not in sub_name:
                    sub_cats1 = sub_cat.xpath('ul/li/a')
                    if sub_cats1:
                        for sub_cat1 in sub_cats1:
                            sub_name1 = sub_cat1.xpath('text()').string()
                            url = sub_cat1.xpath('@href').string()
                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                    else:
                        url = sub_cat.xpath('a/@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//li[contains(@class, "product-card")]/div[h3]')
    for prod in prods:
        name = prod.xpath("h3/a/text()").string()
        url = prod.xpath("h3/a/@href").string()

        reviews = prod.xpath("p/@data-of")
        if reviews:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, context)


def process_product(data, context, session):
    strip_namespace(data)

    pr = dict()
    pr['name'] = context['name']
    pr['url'] = context['url']
    pr['ssid'] = data.xpath('//div[contains(@class, "preview-badge")]/@data-id').string()
    pr['category'] = context['cat']
    pr['manufacturer'] = data.xpath('//div/header[contains(@class, "mobile")]/ul/li/a/span[contains(@class, "strong")]/text()').string()
    pr['mpn'] = data.xpath('//p/span[contains(text(), "SKU:")]/following-sibling::text()').string()
    pr['ean'] = data.xpath('//p/span[contains(text(), "Barcode:")]/following-sibling::text()').string()

    if pr['ssid'] and not session.seen(pr['ssid']):
        session.queue(RequestRevs(pr['ssid'], 1), process_reviews, dict(product=pr))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']
    product.sku = product.ssid
    product.category = context['product']['category']
    product.manufacturer = context['product']['manufacturer']

    mpn = context['product']['mpn']
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = context['product']['ssid']
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs_json = simplejson.loads(data.content)

    revs = data.parse_fragment(revs_json.get('html', '')).xpath('//div[contains(@class, "reviews")]/div')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath("@data-review-id").string()

        date = rev.xpath('.//span[contains(@class, "timestamp")]/@data-content').string()
        if date:
            review.date = date.split()[0]

        author = rev.xpath('.//span[contains(@class, "rev__author")]//text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span/@data-score').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.xpath('.//span[contains(@class, "buyer-badge")]/span[contains(@class, "buyer-badge")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.xpath('.//b[contains(@class, "rev__title")]/text()').string()
        excerpt = rev.xpath('.//div[contains(@class, "rev__body")]//text()').string(multiple=True)
        if excerpt and len(excerpt) > 2:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    revs_cnt = revs_json.get('total_count')
    offset = context.get('offset', 0) + 5
    if offset < revs_cnt:
        next_page = context.get('page', 1) + 1
        session.queue(RequestRevs(product.ssid, next_page), process_reviews, dict(context, offset=offset, page=next_page))
