from agent import *
from models.products import *
import simplejson
import time
import random


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.loot.co.za/search?offset=0&cat=b", use='curl', max_age=0, force_charset='utf-8'), process_prodlist, dict())


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    prods_cnt = context.get('prod_cnt', 0)
    offset = context.get("offset", 0) + 24

    resp = data.xpath('//script[@id="__NEXT_DATA__"]//text()').string()
    if resp:
        prods_json = simplejson.loads(resp).get('props', {}).get('pageProps', {}).get('initialState', {}).get('searchResult', {})

        if not prods_cnt:
            prods_cnt = prods_json.get('hits')
            if prods_cnt:
                prods_cnt = int(prods_cnt)

        prods = prods_json.get('products', [])
        for prod in prods:
            prod_info = prod.get('productInfo')
            rating_cnt = int(prod_info.get('ratingCount'))
            if rating_cnt and rating_cnt > 0:
                url = "https://www.loot.co.za" + prod_info["shareLink"]["uri"]
                session.queue(Request(url, use='curl', max_age=0, force_charset='utf-8'), process_product, dict(url=url))
    else:
        offset -= 23    # Error 502

    if offset < int(prods_cnt):
        url = "https://www.loot.co.za/search?offset=" + str(offset) + "&cat=b"
        session.queue(Request(url, use='curl', max_age=0, force_charset='utf-8'), process_prodlist, dict(context, offset=offset, prods_cnt=prods_cnt))


def process_product(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    resp = data.xpath("//script[@id='__NEXT_DATA__']//text()").string()
    try:
        json = simplejson.loads(resp)
    except:
        return

    prod_data = json.get('props', {}).get('pageProps', {}).get('initialProps', {}).get('product', {})
    product = Product()
    product.name = prod_data.get('productInfo', {}).get("fullTitle")
    product.url = context["url"]
    product.manufacturer = prod_data.get('details', {}).get('General', {}).get('Brand')

    product.ssid = prod_data.get('details', {}).get('General', {}).get('ISBN-13')
    if not product.ssid:
        product.ssid = prod_data.get('productInfo', {}).get("code")

    mpn = prod_data.get('details', {}).get('General', {}).get('LSN')
    if mpn:
        product.add_property(type="id.manufacturer", value=mpn)

    ean = prod_data.get('details', {}).get('General', {}).get('Barcode')
    if ean:
        product.add_property(type="id.ean", value=ean)

    product.category = prod_data.get('parent', {}).get('name')
    if not product.category:
        product.category = 'Tech'

    revs = prod_data.get('reviews', {}).get('results', [])
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.date = rev.get("createdDate")

        author = rev.get("reviewer")
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall or grade_overall == 0:
            value = float(grade_overall)
            review.grades.append(Grade(type="overall", value=value, best=5.0, worst=0.0))

        title = rev.get("title")
        excerpt = rev.get("review")
        if excerpt and excerpt != 'no review':
            review.title = title
        else:
            excerpt = title

        if excerpt and excerpt != 'no review':
            review.add_property(type="excerpt", value=excerpt)

            ssid = rev.get("id")
            if ssid:
                review.ssid = str(ssid)
            else:
                review.ssid = review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
