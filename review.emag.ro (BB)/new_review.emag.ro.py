#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ['Branduri de TOP', 'Resigilate', 'Alege produsul potrivit:', 'Servicii Instalare - Montaj', 'Montare electrocasnice', 'Montare aer conditionat']


def Request(url):
    r = agent.Request(url, proxies=['eu'], force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://sapi.emag.ro/layout/menu/267?source_id=7'), process_catlist, dict(cat='Electrocasnice & Climatizare'))
    # session.queue(Request('https://www.emag.ro'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//li[contains(@class, "megamenu-list-department") and @data-id]')
    for cat in cats:
        cat_id = cat.xpath('@data-id').string()
        name = cat.xpath('.//span[contains(@class, "department-name")]//text()').string()
        if cat_id and name and name not in XCAT:
            url = 'https://sapi.emag.ro/layout/menu/' + cat_id + '?source_id=7'
            session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data: Response, context: dict[str, str], session: Session):
    try:
        quick_nav = simplejson.loads(data.content).get('data', {}).get('items', {}).get('quick_nav', [])
    except:
        return

    cats1 = []
    for nav_col in quick_nav:
        for item in nav_col:
            if item.get('is_heading'):
                cats1.append({'cat1': item, 'subcats': []})
            else:
                if not cats1:
                    cats1.append({'cat1': {}, 'subcats': []})
                cats1[-1]['subcats'].append(item)

    for item in cats1:
        cat1 = item['cat1']
        cat1_name = cat1.get('title', '').strip()

        if cat1_name not in XCAT:
            subcats = item['subcats']
            if subcats:
                for subcat in subcats:
                    subcat_name = subcat.get('title', '').strip()
                    uri = (subcat.get('link') or {}).get('uri', '').split('?')[0]

                    if subcat_name and subcat_name not in XCAT and uri and not uri.startswith(('/label/', '/shop/', '/shopping-assistant/', '/lps/', '/resigilate/')):
                        url = 'https://www.emag.ro' + uri if not uri.startswith('http') else uri
                        cat = context['cat'] + '|' + cat1_name + '|' + subcat_name if cat1_name else context['cat'] + '|' + subcat_name
                        if not session.seen(url):
                            session.queue(Request(url), process_prodlist, dict(cat=cat))
            else:
                uri = (cat1.get('link') or {}).get('uri', '').split('?')[0]

                if cat1_name and uri and not uri.startswith(('/label/', '/shop/', '/shopping-assistant/', '/lps/', '/resigilate/')):
                    url = 'https://www.emag.ro' + uri if not uri.startswith('http') else uri
                    if not session.seen(url):
                        session.queue(Request(url), process_prodlist, dict(cat=context['cat'] + '|' + cat1_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//a[contains(@class, "product-title")]/@href').strings()
    for url in prods:
        if url and not session.seen(url):
            session.queue(Request(url), process_product, dict(context, url=url))

    next_url = data.xpath('//a[@aria-label="Next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.category = context['cat']

    info_str = data.xpath("//script[contains(.,'\"@type\": \"Product\"')]//text()").string()
    if not info_str:
        return # Not a product

    try:
        info = simplejson.loads(info_str)
    except:
        return
    
    product.description = info['description']
    product.name = info['name']
    product.url = info['url']
    product.sku = info['sku']
    product.ssid = product.sku
    product.manufacturer = info['brand']['name']

    revs_count = info.get('aggregateRating')
    if not revs_count:
        return
    revs_count = revs_count.get('reviewCount')
    if int(revs_count) == 0:
        return

    mpn = data.xpath("//span[@class='product-code-display pull-left']//text()").string()
    if mpn:
        mpn = mpn.replace('Cod produs:', '').strip()
        product.properties.append(ProductProperty(type='id.manufacturer', value=mpn))
    
    revs = data.xpath("//div[@class='product-review-item js-review-item row']")

    revs_count = 0
    for rev in revs:
        review = Review()
        review.title = rev.xpath(".//h3[@class='product-review-title']//text()").string(multiple=True)
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath(".//p[@class='small text-muted mrg-sep-none']//text()").string()
        
        author_name = rev.xpath(".//p[@class='product-review-author mrg-top-xs semibold']//text()").string()
        review.authors.append(Person(name=author_name, ssid=author_name))
        
        grade_overall = rev.xpath(".//div[contains(@class,'star-rating-inner')]/@style").string()
        if grade_overall:
            grade_overall = int(grade_overall.split('width:')[1].split('%')[0]) / 20
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))
        
        excerpt = rev.xpath(".//div[contains(@class,'review-body-container')]//text()").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
        
            review.ssid = rev.xpath("@data-id").string()
            product.reviews.append(review)
            revs_count += 1

    if product.reviews:
        session.emit(product)
    
    if revs_count >= 10:
        revs_urn = context['url'].replace('https://www.emag.ro/', '')
        offset = context.get('offset', 0) + 10
        revs_url = 'https://www.emag.ro/product-feedback/' + revs_urn + 'reviews/list?token=&page[offset]=' + str(offset) + '&page[limit]=10&sort[votes]=desc'
        session.queue(Request(revs_url), process_reviews, dict(context, offset=offset, description=product.description, name=product.name, p_url=product.url, sku=product.sku, manufacturer=product.manufacturer))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.category = context['cat']
    product.description = context['description']
    product.name = context['name']
    product.url = context['p_url']
    product.sku = context['sku']
    product.ssid = product.sku
    product.manufacturer = context['manufacturer']

    try:
        resp = simplejson.loads(data.content)
    except:
        return
    
    revs_count = 0

    revs = resp['reviews'].get('items', [])
    for rev in revs:
        review = Review()
        review.title = rev['title']
        review.type = 'user'
        review.url = product.url
        review.date = rev['created'].split('T')[0]
        
        author_name = rev['user']['name']
        review.authors.append(Person(name=author_name, ssid=author_name))
        
        grade_overall = rev['rating']
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))
        
        excerpt = rev['content_no_tags']
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
        
            review.ssid = str(rev['id'])
            product.reviews.append(review)
            revs_count += 1

    if product.reviews:
        session.emit(product)

    if revs_count >= 10:
        revs_urn = context['url'].replace('https://www.emag.ro/', '')
        offset = context.get('offset', 0) + 10
        revs_url = 'https://www.emag.ro/product-feedback/' + revs_urn + 'reviews/list?token=&page[offset]=' + str(offset) + '&page[limit]=10&sort[votes]=desc'
        session.queue(Request(revs_url), process_reviews, dict(context, offset=offset))
