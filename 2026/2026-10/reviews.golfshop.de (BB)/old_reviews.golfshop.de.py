#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ['SUPER-SALE %', 'Marken']


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
    r = agent.Request(url, force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.golfshop.de/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ul[@role="menubar"]/li/a')
    cnt = 0
    for cat in cats:
        url = cat.xpath('@href').string()
        name = cat.xpath('span//text()').string()

        if name and name not in XCAT:
            cnt += 1

            cats1 = data.xpath('//div[@class="advanced-menu"]/div[{}]//li[contains(@class, "item--level-0")]'.format(cnt))
            if cats1:
                for cat1 in cats1:
                    url = cat1.xpath('a/@href').string()
                    cat1_name = cat1.xpath('a//text()').string()

                    subcats = cat1.xpath('ul/li/a')
                    if subcats:
                        for subcat in subcats:
                            url = subcat.xpath('@href').string()
                            subcat_name = subcat.xpath('text()').string()
                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name))

                    else:
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name))
            else:
                session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "product--box")]')
    for prod in prods:
        url = prod.xpath('.//a[@class="product--title"]/@href').string()
        mpn = prod.xpath('@data-ordernumber').string()

        rating = prod.xpath('.//span[@class="product--rating"]')
        if rating and url and not session.seen(url):
            session.queue(Request(url), process_product, dict(context, url=url, mpn=mpn))

    next_url = data.xpath('//a[@title="Nächste Seite"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = data.xpath('//h1[@class="product--title"]//text()').string()
    product.category = context['cat']
    product.url = context['url']
    product.manufacturer = data.xpath('//meta[@property="product:brand"]/@content').string()
    product.ssid = data.xpath('//meta[@itemprop="productID"]/@content').string()

    mpn = context.get('mpn')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean:
        product.add_property(type='id.ean', value=ean)


    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//meta[@itemprop="datePublished"]/@content').string()

        title = rev.xpath('.//h4[@class="content--title"]//text()').string()
        if title and title.lower() != "bewertung eines golfshop.de kunden":
            review.title = title

        author = rev.xpath('.//span[@itemprop="author"]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//meta[@itemprop="ratingValue"]/@content').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//p[@itemprop="reviewBody"]//text()').string(multiple=True)
        if excerpt and excerpt.strip():
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            if not session.seen(review.ssid):
                product.reviews.append(review)

    if product.reviews:
        session.emit(product)
