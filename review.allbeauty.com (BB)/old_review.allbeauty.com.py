#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ["Brands", "Offers", "New In", "Discover", "Featured Brands", "Skin Type & Concern", "Shop by Ingredient", "New In Men"]


def RequestRevs(pid, offset):
    url = "https://www.allbeauty.com/api/commerce?operation=ReviewList"
    fdata = """{"variables":{"sku":""" + pid + ""","hasReviews":true,"limit":10,"offset":""" + str(offset) + ""","hasReviewsVoting":true},"horizonApq":false,"application":"storefront"}"""
    r = agent.Request(url, force_charset='utf-8', max_age=0, data=fdata, method='POST')
    r.add_header('Content-Type', 'application/json')
    r.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0')
    r.add_header('Accept', '*/*')
    r.add_header('Accept-Encoding', 'gzip, deflate, br')
    return r


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0:', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.allbeauty.com/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//nav[@id="main-nav"]/div/ul/li')
    for cat in cats:
        name = cat.xpath('div/a/span//text()').string()
        if name not in XCAT:
            cats1 = cat.xpath('.//div[@role="group"]/ul/div/li/div')
            for cat1 in cats1:
                cat1_name = cat1.xpath('div/*//text()').string()
                if cat1_name not in XCAT and "shop all" not in cat1_name.lower():
                    if ' by ' in cat1_name:
                        cat1_name = ''
                    subcats = cat1.xpath('ul/li/div/a')
                    for subcat in subcats:
                        url = subcat.xpath('@href').string()
                        subcat_name = subcat.xpath('text()').string()
                        if subcat_name not in XCAT:
                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[@data-testid="product-item"]')
    for prod in prods:
        pr = dict()
        pr['name'] = prod.xpath('.//a[@data-testid="product-title"]//text()').string()
        pr['category'] = context['cat'].replace('||', '|')
        pr['url'] = prod.xpath('.//a[@data-testid="product-title"]/@href').string()
        pr['ssid'] = pr['url'].split('/')[-2]
        pr['sku'] = pr['ssid']
        if not session.seen(pr['ssid']):
            session.queue(RequestRevs(pr['ssid'], 0), process_reviews, dict(product=pr))

    next_url = data.xpath('//a[@id="next-page"]/@href').string()
    if next_url and not session.seen(next_url):
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.category = context['product']['category']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']
    product.sku = context['product']['sku']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('data', {}).get('product', {}).get('reviews', {}).get('reviews', {}).get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev['id']
        review.date = rev.get('posted')

        author = rev.get('authorName')
        if author:
            review.authors.append(Person(name=author, ssid=author))


        is_verified = rev.get('verifiedPurchase')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('positiveVotes')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('negativeVotes')
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        elements = rev.get('elements', [{}])
        for el in elements:
            if el.get('key') == "score":
                review.grades.append(Grade(type='overall', value=float(el['score']), best=5.0))

            if el.get('key') == "content":
                excerpt = el.get('value')
                if excerpt:
                    title = rev.get('title')
                    if title and title.strip('.') not in excerpt:
                        review.title = title

                    review.add_property(type='excerpt', value=excerpt)

                    product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    revs_cnt = context.get('revs_cnt', revs_json.get('data', {}).get('product', {}).get('reviews', {}).get('total'))
    offset = context.get('offset', 0) + 10
    if revs_cnt and int(revs_cnt) > offset:
        session.queue(RequestRevs(product.ssid, offset), process_reviews, dict(context, revs_cnt=revs_cnt, offset=offset))
