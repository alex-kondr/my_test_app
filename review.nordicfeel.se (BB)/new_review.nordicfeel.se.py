#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = [u'Bästsäljare', u'Nyheter', u'Varumärken', u'Kampanjer']


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
    r = agent.Request(url, force_charset="utf-8")
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.nordicfeel.com/se'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ul[@role="menubar"]/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    subcats = data.xpath('//div[contains(@class, "intro__sublinks")]/a')
    for subcat in subcats:
        name = subcat.xpath('.//text()').string(multiple=True)
        url = subcat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=context['cat']+'|'+name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//a[contains(@class, "product-list-item") and div[contains(@class, "item__name")]]')
    for prod in prods:
        name = prod.xpath('div[contains(@class, "item__name")]/text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(@aria-label, "next") and not(contains(@class, "disabled"))]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    pr = dict()
    pr['name'] = context['name']
    pr['url'] = context['url']
    pr['ssid'] = data.xpath('//div/@data-sku').string()
    pr['category'] = context['cat']
    pr['manufacturer'] = data.xpath('//span[@class="brand-link__text"]/text()').string()
    pr['ean'] = data.xpath('//div[@class="syncle-product-gtin"]/text()').string()

    try:
        prods_info_json = simplejson.loads(data.xpath('//script[@data-nuxt-data="nuxt-app"]/text()').string())
        for info in prods_info_json:
            if 'cr.testfreaks.com/reviews/page.json' in str(info):
                if not session.seen(pr['ssid']):
                    session.queue(Request(info), process_reviews, dict(product=pr, revs_url=info))
                return
    except:
        return


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']
    product.sku = product.ssid
    product.category = context['product']['category']
    product.manufacturer = context['product']['manufacturer']

    ean = context['product']['ean']
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('reviews', [])
    for rev in revs:

        lng = rev.get('lang')
        if lng != 'sv':
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.get('date')

        author = rev.get('author', {})
        if author and "anonym" not in author.lower():
            review.authors.append(Person(name=author, ssid=author))
        else:
            author = None

        grade_overall = rev.get('score')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('verified_buyer')
        if is_verified_buyer is True:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('votes_up')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('votes_down')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        excerpt = rev.get('extract')
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    next_url = revs_json.get('next_page_url')
    if next_url:
        session.queue(Request(next_url), process_reviews, dict(context))
