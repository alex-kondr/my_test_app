#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ['SUPER-SALE %', 'Marken', 'Home', 'Bestseller', 'SALE']


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
    r = agent.Request(url, force_charset='utf-8', proxies=['rotating-us', 'rotating-eu'])
    return r


def RequestRevs(sku):
    sku = sku.encode("hex")
    url = 'https://integrations.etrusted.com/feeds/product-reviews/v1/channels/chl-5af0c86e-20c2-43bb-94ca-474aad10ca7a/sku/{}/default/all/feed.json?widgetId=wdg-7b9027f8-1f25-48cd-9c63-2189fdfff1c8&channelId=chl-5af0c86e-20c2-43bb-94ca-474aad10ca7a&showUGC=true'.format(sku)
    r = agent.Request(url, force_charset='utf-8', proxies=['rotating-us'])
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.golfshop.de/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//nav[@role="navigation"]/ul/li')
    for cat in cats:
        name = cat.xpath('(a|details/summary//span)//text()').string()

        if name and name not in XCAT:
            cats1 = cat.xpath('details//div[@class="mega-menu__item"]')
            if cats1:
                for cat1 in cats1:
                    cat1_name = cat1.xpath('a//text()').string()

                    subcats = cat1.xpath('ul/li/a')
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.xpath('.//text()').string(multiple=True)
                            url = subcat.xpath('@href').string()
                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name))
                    else:
                        url = cat1.xpath('a/@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name))
            else:
                url = cat.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//h3[contains(@class, "product-card__title")]/a')
    for prod in prods:
        name = prod.xpath('.//text()').string(multiple=True)
        url = prod.xpath('@href').string()

        if not session.seen(url):
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    pr = dict()
    pr['name'] = context['name']
    pr['url'] = context['url']
    pr['ssid'] = data.xpath('//product-info/@data-product-id').string()
    pr['category'] = context['cat'].replace(' / ', '/')
    pr['manufacturer'] = data.xpath('//p[contains(@class, "product__vendor")]/a/text()').string()
    pr['mpn'] = data.xpath('//p[contains(@class, "product__sku")]/span[not(contains(., "Artikelnummer"))]/text()').string()

    try:
        prod_json = data.xpath('''//script[contains(., '"barcode":"')]/text()''').string()
        prod_json = simplejson.loads(prod_json)
        pr['ean'] = prod_json.get('barcode')
    except:
        pass

    try:
        prod_json = data.xpath('''//script[contains(., '"reviewCount": "')]/text()''').string()
        prod_json = simplejson.loads(prod_json)

        revs_cnt = prod_json.get('aggregateRating', {}).get('reviewCount', 0)
    except:
        return

    skus = data.xpath('//etrusted-widget/@data-sku').string()
    if skus:
        skus = skus.split(',')
        for sku in skus:
            if not session.seen(sku) and revs_cnt and int(revs_cnt) > 0:
                session.queue(RequestRevs(sku), process_reviews, dict(product=pr))


def process_reviews(data: Response, context: dict[str, str], session: Session):
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

    ean = context['product'].get('ean')
    if ean and str(ean).isdigit() and len(str(ean)) > 10:
        product.add_property(type='id.ean', value=str(ean))

    try:
        revs = simplejson.loads(data.content)
    except:
        return

    for rev in revs:
        if rev.get('language') != 'de' or rev.get('syndicated') is True:
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('submittedAt')
        if date:
            review.date = date.split('T')[0]

        # no author

        grade_overall = rev.get('rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('isVerified')
        if is_verified_buyer is True:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('title')
        excerpt = rev.get('comment')
        if excerpt:
            if title and title.strip() != excerpt.strip():
                review.title = title
        else:
            excerpt = title

        if excerpt and excerpt.strip():
            review.add_property(type='excerpt', value=excerpt.strip())

            ssid = rev.get('id')
            if ssid:
                review.ssid = ssid.replace('rev-', '')
            else:
                review.ssid = review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
