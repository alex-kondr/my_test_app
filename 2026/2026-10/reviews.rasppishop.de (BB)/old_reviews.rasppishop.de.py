#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


XCAT = ['Hersteller']


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace('xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def Request(url):
    r = agent.Request(url, force_charset='utf-8')
    return r


def RequestRevs(url, page):
    url = url + '?ratings_nPage=' + str(page)
    r = agent.Request(url, force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.rasppishop.de/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="nav-mobile-body"]/ul/li')
    for cat in cats:
        name = cat.xpath('a/span//text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('.//div[@class="container subcategory-wrapper"]/ul/li/a')

            for cat1 in cats1:
                url = cat1.xpath('@href').string()
                cat1_name = cat1.xpath('span//text()').string().replace(' | ', '/')
                session.queue(Request(url), process_category, dict(cat=name + '|' + cat1_name))


def process_category(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    subcats = data.xpath('//div[@class="collapse snippets-categories-collapse show"]/ul/li')
    if not subcats:
        process_prodlist(data: Response, context: dict[str, str], session: Session)
        return

    for subcat in subcats:
        url = subcat.xpath('a/@href').string() or subcat.xpath('span/a/@href').string()
        subcat_name = subcat.xpath('a//text()').string() or subcat.xpath('span/a//text()').string()
        subcat_name = subcat_name.replace(' | ', '/')
        session.queue(Request(url), process_prodlist, dict(cat=context['cat'] + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="productbox-inner"]')
    for prod in prods:
        url = prod.xpath('.//div[@itemprop="name"]/a/@href').string()
        name = prod.xpath('.//div[@itemprop="name"]/a//text()').string()
        rating = prod.xpath('.//a[@class="rating"]')
        if rating:
            session.queue(Request(url), process_product, dict(context, url=url, name=name))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url and not session.seen(next_url):
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    pr = dict()
    pr['name'] = context['name']
    pr['category'] = context['cat']
    pr['url'] = context['url']
    pr['manufacturer'] = data.xpath('//tr[@itemprop="brand"]/td//span[@itemprop="name"]/text()').string()

    pr['ean'] = data.xpath('//span[@itemprop="gtin13"]/text()').string()
    pr['sku'] = data.xpath('//span[@itemprop="sku"]/text()').string()
    pr['ssid'] = pr['sku']

    revs_cnt = data.xpath('//meta[@itemprop="reviewCount"]/@content').string()
    if revs_cnt and int(revs_cnt) > 0 and pr['ssid'] and not session.seen(pr['ssid']):
        session.queue(RequestRevs(pr['url'], 0), process_reviews, dict(product=pr, revs_cnt=int(revs_cnt)))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['product']['name']
    product.category = context['product']['category']
    product.url = context['product']['url']
    product.sku = context['product']['sku']
    product.ssid = context['product']['ssid']
    product.manufacturer = context['product'].get('manufacturer')

    ean = context['product'].get('ean')
    if ean:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.title = rev.xpath('span[@itemprop="name"]//text()').string()
        review.date = rev.xpath('.//meta[@itemprop="datePublished"]/@content').string()

        author = rev.xpath('.//span[@itemprop="author"]/span/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        is_verified = rev.xpath('.//span[@class="verified-purchase"]/text()').string()
        if is_verified and is_verified.lower() == "verifizierter kauf":
            review.add_property(type='is_verified_buyer', value=True)

        grade_overall = rev.xpath('.//span[@class="rating"]/@title').string()
        if grade_overall:
            grade_overall = grade_overall.split(': ')[-1].split('/')[0]
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//p[@itemprop="reviewBody"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    offset = context.get('offset', 0) + 10
    if context['revs_cnt'] > offset:
        next_page = context.get('page', 0) + 1
        session.queue(RequestRevs(product.url, next_page), process_reviews, dict(context, offset=offset, page=next_page))
