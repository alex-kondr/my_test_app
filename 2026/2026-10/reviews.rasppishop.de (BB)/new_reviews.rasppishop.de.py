#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


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

    cats = data.xpath('//div[contains(@class, "nav-mobile")]/ul/li')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        if name not in XCAT:
            cats1 = cat.xpath('.//div[contains(@class, "subcategory")]/div/div[a/@class]')

            for cat1 in cats1:
                cat1_name = cat1.xpath('a/span//text()').string()

                subcats = cat1.xpath('div/ul/li/a')
                if subcats:
                    for subcat in subcats:
                        subcat_name = subcat.xpath('.//text()').string(multiple=True)
                        url = subcat.xpath('@href').string()
                        session.queue(Request(url+'?Sortierung=12'), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                else:
                    url = cat1.xpath('a/@href').string()
                    session.queue(Request(url+'?Sortierung=12'), process_prodlist, dict(cat=name+'|'+cat1_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[div[@class="productbox-title"]]')
    for prod in prods:
        name = prod.xpath('div[@class="productbox-title"]/a//text()').string()
        url = prod.xpath('div[@class="productbox-title"]/a/@href').string()

        rating = prod.xpath('div/a[@class="rating"]')
        if rating and not session.seen(url):
            session.queue(Request(url), process_product, dict(context, url=url, name=name))
        else:
            return

    next_url = data.xpath('//a[@aria-label="weiter"]/@href').string()
    if next_url and not session.seen(next_url):
        session.queue(Request(next_url+'?Sortierung=12'), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    pr = dict()
    pr['name'] = context['name']
    pr['url'] = context['url']
    pr['ssid'] = data.xpath('//span[@itemprop="sku"]/text()').string()
    pr['category'] = context['cat'].replace(' | ', '/').replace(' / ', '/')
    pr['manufacturer'] = data.xpath('//tr[td[@class="product-manufacturer"]]//span[@itemprop="name"]/text()').string()
    pr['ean'] = data.xpath('//span[@itemprop="gtin13"]/text()').string()

    revs_cnt = data.xpath('//meta[@itemprop="reviewCount"]/@content').string()
    if revs_cnt and int(revs_cnt) > 0 and pr['ssid'] and not session.seen(pr['ssid']):
        session.queue(RequestRevs(pr['url'], 0), process_reviews, dict(product=pr, revs_cnt=int(revs_cnt)))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']
    product.sku = product.ssid
    product.category = context['product']['category']
    product.manufacturer = context['product']['manufacturer']

    ean = context['product'].get('ean')
    if ean and ean.isdigit() and len(ean) > 0:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[contains(@class, "review-comment")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//meta[@itemprop="datePublished"]/@content').string()

        author = rev.xpath('.//span[@itemprop="author"]/span[@itemprop="name"]/text()').string()
        if author and 'anonym' not in author.lower():
            review.authors.append(Person(name=author, ssid=author))
        else:
            author = None

        grade_overall = rev.xpath('.//span[@class="rating"]/@title').string()
        if grade_overall:
            grade_overall = grade_overall.split(': ')[-1].split('/')[0]
            if float(grade_overall) > 0:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//span[@class="verified-purchase"]/text()').string()
        if is_verified and is_verified.lower() == "verifizierter kauf":
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.xpath('.//span[@class="subheadline"]//text()').string()
        excerpt = rev.xpath('.//p[@itemprop="reviewBody"]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            ssid = rev.xpath('@id').string()
            if ssid:
                review.ssid = ssid.replace('comment', '').strip()
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    offset = context.get('offset', 0) + 10
    if context['revs_cnt'] > offset:
        next_page = context.get('page', 0) + 1
        session.queue(RequestRevs(product.url, next_page), process_reviews, dict(context, offset=offset, page=next_page))
