#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


import _proxies_config
reload(_proxies_config)
PROXIES = _proxies_config.us_rotating_proxies + _proxies_config.eu_rotating_proxies + _proxies_config.ap_rotating_proxies


def Request(url):
    options = "-H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 11.1; rv:84.0) Gecko/20100101 Firefox/84.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8' -H 'Accept-Language: ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3' --compressed -H 'Connection: keep-alive' -H 'Upgrade-Insecure-Requests: 1' -H 'Cache-Control: max-age=0'"
    r = agent.Request(url, use='curl', options='-s -L --insecure '+options, max_age=0, proxies=PROXIES)
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.emag.ro'), process_frontpage, dict())
    # session.queue(Request('https://www.emag.ro/aparat-hibrid-de-barbierit-si-tuns-barba-philips-oneblade-4-piepteni-1-lama-negru-verde-qp2530-30/pd/D3DGD4BBM/'), process_product, dict(url='https://www.emag.ro/aparat-hibrid-de-barbierit-si-tuns-barba-philips-oneblade-4-piepteni-1-lama-negru-verde-qp2530-30/pd/D3DGD4BBM/', cat='cat', name='name'))


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath("//li[@class='megamenu-list-department js-megamenu-list-department']/a")
    for cat in cats:
        url = cat.xpath("@href").string()
        name = cat.xpath(".//text()").string(multiple=True)
        if url and name and not session.seen(url):
            session.queue(Request(url), process_category, dict(context, url=url, cat=name))


def process_category(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath("//ul[@class='emg-aside-links']/li/a")
    for cat in cats:
        url = cat.xpath("@href").string()
        name = cat.xpath(".//text()").string()
        if url and name and not session.seen(url):
            session.queue(Request(url), process_category, dict(context, url=url, cat=context['cat']+'|'+name))

    if not cats:
        process_subcategory(data: Response, context: dict[str, str], session: Session)


def process_subcategory(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath("//a[@class='product-title js-product-url']")
    for prod in prods:
        url = prod.xpath("@href").string()
        session.queue(Request(url), process_product, dict(context, url=url))
    
    next_url = data.xpath("//a[@aria-label='Next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_subcategory, dict(context))


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
