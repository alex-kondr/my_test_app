#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


XCAT = ['TODAS']


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
    options = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""
    r = agent.Request(url, proxies=['rotating-us'], use='curl', force_charset='utf-8', options='-s -L --insecure '+options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.dolce-gusto.es/capsulas'), process_category, dict(cat='Capsulas'))
    session.queue(Request('https://www.dolce-gusto.es/cafeteras'), process_category, dict(cat='Cafeteras'))
    session.queue(Request('https://www.dolce-gusto.es/accesorios'), process_category, dict(cat='Accesorios'))


def process_category(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    subcats = data.xpath('//div[contains(@class, "_subcategories")]/div/a')
    for subcat in subcats:
        name = subcat.xpath('text()').string()
        url = subcat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_prodlist, dict(cat=context['cat']+'|'+name.lower().capitalize()))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "product-card__content")]')
    for prod in prods:
        name = prod.xpath('.//a[contains(@class, "product-card__name")]/text()').string()
        url = prod.xpath('.//a[contains(@class, "product-card__name")]/@href').string()

        revs_cnt = prod.xpath('//div[contains(@class, "product__reviews")]/a/text()').string()
        if revs_cnt and int(revs_cnt.strip('( )')) > 0:
            url = 'https://www.dolce-gusto.es/' + url.rstrip('/').split('/')[-1]
            if not session.seen(url):
                session.queue(Request(url), process_product, dict(context, name=name, url=url))

    # No next page


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs_json = data.xpath("""//script[contains(., '"@type":"Product"')]/text()""").string()
    if not revs_json:
        return

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="product"]/@value').string()
    product.sku = data.xpath('//div/dd[contains(@class, "product-detail-value")]/text()').string()
    product.category = context['cat']
    product.manufacturer = 'Dolce Gusto'

    mpn = data.xpath('//div/button/@data-guid').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    revs = simplejson.loads(revs_json).get('review')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('datePublished')
        if date:
            review.date = date.split()[0]

        author = rev.get('author', {}).get('name')
        if author:
            author = author.strip()
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('reviewRating', {}).get('ratingValue')
        if grade_overall:
            grade_overall = float(grade_overall) / 20
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.get('name')
        excerpt = rev.get('description')
        if excerpt and len(excerpt.strip()) > 2:
            if title:
                review.title = title.strip()
        elif title:
            excerpt = title

        if excerpt:
            excerpt = excerpt.strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)
