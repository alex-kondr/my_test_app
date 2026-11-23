#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from datetime import datetime


XCAT = ['Health Resource Center', 'Featured']


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
    session.queue(Request('https://www.1mg.com/pwa-dweb-api/api/v4/udp_tree'), process_frontpage, dict())

    # Fot testing
    # session.queue(Request('https://www.1mg.com/categories/health-conditions/stomach-care-30?filter=true&sort=rati
    # ng&pageNumber=80'), process_category, dict(cat='cat'))
    # session.queue(Request('https://www.1mg.com/otc/listerine-cool-mint-mouth-wash-otc323043/reviews'), process_reviews, dict(cat='cat', name='name', url='https://www.1mg.com/otc/listerine-cool-mint-mouth-wash-otc323043', revs_url='https://www.1mg.com/otc/listerine-cool-mint-mouth-wash-otc323043/reviews'))


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    try:
        cats = simplejson.loads(data.content).get('data', {}).get('udp_tree', [])
    except:
        return

    for cat in cats:
        name = cat.get('name').strip()

        if name not in XCAT:
            subcats = cat.get('children', [])
            for subcat in subcats:
                subcat_name = subcat.get('name').strip()
                url = 'https://www.1mg.com' + subcat.get('slug') +'?filter=true&sort=rating'

                if url and name and subcat_name and not subcat_name.startswith('All ') and not session.seen(url):
                    session.queue(Request(url), process_prodlist, dict(cat=name+'|'+subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "cardContainer")]/a')
    for prod in prods:
        name = prod.xpath('.//div[contains(@class, "ProductTile")]/text()').string()
        url = prod.xpath('@href').string()

        revs_cnt = prod.xpath('.//div[contains(@class, "textSecondary RatingBadge")]/text()').string()
        if revs_cnt and int(revs_cnt.strip('( )')) > 0 and not session.seen(url):
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url+'&filter=true&sort=rating'), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = dict()
    product['name'] = context['name']
    product['url'] = context['url']
    product['ssid']


def process_reviews(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    info = data.xpath("//script[@type='application/ld+json']//text()").string()
    if not info:
        return
    info = simplejson.loads(info)

    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.ssid = str(info['sku'])
    product.sku = product.ssid
    product.manufacturer = info['brand']

    revs = data.xpath("//div[contains(@class,'ReviewCards__review-card')]")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['revs_url']
        review.date = rev.xpath(".//div[contains(@class,'ReviewCards__date')]//text()").string()

        author_name = rev.xpath(".//div[contains(@class,'ReviewCards__name')]//text()").string()
        review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = rev.xpath(".//div[contains(@class,'Rating__ratings-container')]/span//text()").string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_ver = rev.xpath(".//span[text()='Verified Buyer']")
        if is_ver:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.xpath(".//div[contains(@class,'ReviewCards__review-description')]//text()").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            review.ssid = review.digest()
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    page = 1
    total_pages = data.xpath("//ul[@class='list-pagination']/li[a[@class='button-text link-page']][last()]/a//text()").string()
    if not total_pages:
        return
    total_pages = int(total_pages)
    if page < total_pages:
        page += 1
        next_url = "https://www.1mg.com/pharmacy_api_gateway/v4/skus/%s/reviews?page=%s&sort_by=rank_score:desc"%(product.ssid, page)
        session.queue(Request(next_url), process_reviews_json, dict(context, page=page, total_pages=total_pages, ssid=product.ssid, man=product.manufacturer))


def process_reviews_json(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = product.ssid
    product.manufacturer = context['man']

    json = simplejson.loads(data.content)
    revs = json['data']['reviews']
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['revs_url']
        review.ssid = str(rev['id'])

        date_stamp = rev['rating_created_at']
        review.date = datetime.utcfromtimestamp(date_stamp).strftime('%d.%m.%Y')

        author_name = rev['reviewer_name']
        review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = str(rev['value'])
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_ver = rev['is_verified']
        if is_ver:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev['review_description']
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    page = context['page']
    total_pages = context['total_pages']
    if page < total_pages:
        page += 1
        next_url = "https://www.1mg.com/pharmacy_api_gateway/v4/skus/%s/reviews?page=%s&sort_by=rank_score:desc"%(product.ssid, page)
        session.queue(Request(next_url), process_reviews_json, dict(context, page=page))
