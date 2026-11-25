#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCATS = ['Уценка', 'Мебель', 'Сад и огород', 'Дом и сад', 'Матрасы', 'Диваны', 'Двери', 'Услуги', 'Сертификаты']


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
    r = agent.Request(url)
    return r


def RequestCats():
    options = """--compressed --header 'Accept: application/json' --header 'Content-Type: application/json' --header 'Cookie: accessToken=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ2ZXIiOjAuMSwiYW5vIjoxLCJleHAiOjE4MjcxNzM4NTMsInN1YiI6ImZmOTY1YmYxLWU3MjAtNGMwMS1hOTg5LThkMGExNjdmMWMzZiIsImlhdCI6MTc5NTYyNzA1M30.1DAJITylqrlWBnUYOs9qYVIHcr-ZwEaZNVT4P3UkiIs; refreshToken=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJmZjk2NWJmMS1lNzIwLTRjMDEtYTk4OS04ZDBhMTY3ZjFjM2YiLCJhbm8iOjEsImV4cCI6MTgyNzE3Mzg1MywiaWF0IjoxNzk1NjI3MDUzLCJ2ZXIiOjAuMX0.gOaBzlUeEzCZkhoTQHOoG1irU9ybuZEIEPFe08pxi2A'"""
    r = agent.Request('https://gate.21vek.by/catalog/catalog', use='curl', options='-s -L --insecure '+options, force_charset='utf-8')
    return r


def RequestRevs(url, offset):
    options = "--compressed -H 'Accept: application/json' -H 'Accept-Encoding: deflate' -H 'Content-Type: application/json'"
    slug = url.strip('/').split('/')[-1].replace('.html', '')
    url = 'https://gate.21vek.by/reviews/product/{slug}/reviews?limit=10&offset={offset}'.format(slug=slug, offset=offset)
    r = agent.Request(url, use='curl', options='-s -L --insecure '+options)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(RequestCats(), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    try:
        cats = simplejson.loads(data.content)
    except:
        return

    for cat in cats:
        name = cat.get('name').strip()

        if name and name not in XCATS:
            cats1 = cat.get('children', [])
            for cat1 in cats1:
                cat1_name = cat1.get('name').strip()

                if cat1_name and cat1_name not in XCATS:
                    subcats = cat1.get('children', [])
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.get('name').strip()
                            url = subcat.get('url')

                            if subcat_name and subcat_name not in XCATS and not subcat.get('isVirtual') and url and not session.seen(url):
                                session.queue(Request(url+'?order[rating]=desc&filter[sa]='), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                    else:
                        url = cat1.get('url')
                        if url and not cat1.get('isVirtual') and not session.seen(url):
                            session.queue(Request(url+'?order[rating]=desc&filter[sa]='), process_prodlist, dict(cat=name+'|'+cat1_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[@data-testid="product-list"]//div[@itemprop="itemListElement"]')
    for prod in prods:
        name = prod.xpath('.//a[@data-testid="card-info"]//text()').string()
        ssid = prod.xpath('@data-id').string()
        url = prod.xpath('.//a[@data-testid="card-info"]/@href').string()

        revs_cnt = prod.xpath('.//meta[@itemprop="reviewCount"]/@content').string()
        if revs_cnt and int(revs_cnt) > 0:
            if ssid:
                ssid = ssid.split('-')[-1]
                if not session.seen(ssid):
                    session.queue(Request(url), process_product, dict(context, name=name, ssid=ssid, url=url, revs_cnt=int(revs_cnt)))
        else:
            return

    next_url = data.xpath('//a[contains(@class, "loadMoreButton")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    pr = dict()
    pr['name'] = context['name']
    pr['url'] = context['url']
    pr['ssid'] = context['ssid']
    pr['category'] = context['cat']

    try:
        prods_json = data.xpath("""//script[contains(., '"@type":"Product"')]/text()""").string()
        prods_json = simplejson.loads(prods_json)

        pr['manufacturer'] = prods_json.get('brand')
    except:
        pass

    session.queue(RequestRevs(pr['url'], 0), process_reviews, dict(context, product=pr))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']
    product.sku = product.ssid
    product.category = context['product']['category']
    product.manufacturer = context['product'].get('manufacturer')

    try:
        revs_json = simplejson.loads(data.content).get('data', {})
    except:
        revs_json = {}

    revs = revs_json.get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('id')

        date = rev.get('dateTimestamp')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('name')
        if author and u'Покупатель 21vek.by' not in author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        pros = rev.get('positives')
        if pros:
            review.add_property(type='pros', value=pros)

        cons = rev.get('negatives')
        if cons:
            review.add_property(type='cons', value=cons)

        excerpt = rev.get('summary')
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    offset = context.get('offset', 0) + 10
    if offset < context['revs_cnt']:
        session.queue(RequestRevs(product.url, offset), process_reviews, dict(context, offset=offset))
