#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.powerreviews_api_reviews import *


XCAT = ["Discover Dermstore", "Brands", "Sale", "Blog", "Popular Categories", "Skin Care Advice", "Shop All", "Home", "Holiday Shop", "Bestsellers", "Sale & Offers", "New", "Text An Expert", "Exclusives"]
XCAT2 = ["shop all", "brands"]


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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.skinstore.com'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//nav[@aria-label="Main menu"]/div')
    for cat in cats:
        name = cat.xpath('div[contains(@class, "nav-controls")]/a//text()').string(multiple=True)

        if name and name not in XCAT:
            cats1 = cat.xpath('div[contains(@class, "navigation")]/div/div')

            for cat1 in cats1:
                cat1_name = cat1.xpath('a//text()').string(multiple=True)

                if cat1_name not in XCAT and not any(word in cat1_name.lower() for word in XCAT2):

                    if 'type' in cat1_name.lower() or 'shop by' in cat1_name.lower() or cat1_name == name:
                        cat1_name = ''

                    subcats = cat1.xpath('div/a')
                    for subcat in subcats:
                        subcat_name = subcat.xpath('text()').string()
                        url = subcat.xpath('@href').string()

                        if subcat_name not in XCAT:
                            session.queue(Request(url), process_prodlist, dict(url=url, cat=name + '|' + cat1_name + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//*[contains(name(), "product-card") and contains(@class, "product-card")]')
    for prod in prods:
        name = prod.xpath('.//a[contains(@class, "item-title")]/text()').string()
        ssid = prod.xpath('@data-quicklook').string()
        url = 'https://www.dermstore.com/p/' + ssid

        if not session.seen(url):
            session.queue(Request(url), process_product, dict(context, url=url, name=name, ssid=ssid))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    pr = dict()
    pr['name'] = context['name']
    pr['url'] = context['url']
    pr['ssid'] = context['ssid']
    pr['id.sku'] = pr['ssid']
    pr['category'] = context['cat'].replace('Shop ', '').replace('||', '|')
    pr['manufacturer'] = data.xpath('//a[contains(@class, "brand title")]/text()').string()

    product = Product()
    product.name = pr['name']
    product.url = pr['url']
    product.ssid = pr['ssid']
    product.sku = product.ssid
    product.category = pr['category']
    product.manufacturer = pr['manufacturer']

    try:
        prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type":"Product"')]//text()''').string())

        pr['id.manufacturer'] = prod_json.get('mpn')
        if pr['id.manufacturer']:
            product.add_property(type='id.manufacturer', value=pr['id.manufacturer'])
    except:
        prod_json = {}

    ean = data.xpath('''//script[contains(., '"barcode":"')]/text()''').string()
    if ean:
        pr['id.ean'] = ean.split('"barcode":"', 1)[-1].split('","', 1)[0]
        if pr['id.ean'] and pr['id.ean'].isdigit() and len(pr['id.ean']) > 10:
            product.add_property(type='id.ean', value=pr['id.ean'])

    revs = prod_json.get('review', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.get('datePublished')

        author = rev.get('author', {}).get('name')
        if author and 'anonym' not in author:
            review.authors.append(Person(name=author, ssid=author))
        else:
            author = None

        grade_overall = rev.get('reviewRating', {}).get('ratingValue')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('reviewBody')
        if excerpt and len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    merchant_id = '678785550'
    locale = 'en_US'
    api_key = 'e8e40c10-869f-458c-981f-34877ef4fecc'

    if pr['ssid'] and not session.seen(pr['ssid']):
        process_reviews_request(data, dict(product=pr, api_key=api_key, merchant_id=merchant_id, locale=locale), session)
