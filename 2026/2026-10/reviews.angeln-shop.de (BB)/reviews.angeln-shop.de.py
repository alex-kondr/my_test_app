#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ['Marken', 'Angebote', 'mehr...', 'Sale', 'Gutscheine & Geschenke']
XCAT2 = ['neuheiten']


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


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.angeln-shop.de/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="navigation-flyout"]/div[@class="container"]')
    for cat in cats:
        name = cat.xpath('div[contains(@class, "flyout-bar")]//a/@title').string()

        if name not in XCAT:
            cats1 = cat.xpath('.//div[contains(@class, "categories is-level-0")]/div')
            for cat1 in cats1:
                cat1_name = cat1.xpath('(div|a)[contains(@class, "is-level-0")]/@title').string()

                subcats = cat1.xpath('div[contains(@class, "is-level-1")]/div/a')
                if subcats:
                    for subcat in subcats:
                        subcat_name = subcat.xpath('@title').string()
                        url = subcat.xpath('@href').string()

                        if name and cat1_name and subcat_name and not any(word in subcat_name.lower() for word in XCAT2):
                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name))
                else:
                    url = cat1.xpath('a[contains(@class, "is-level-0")]/@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "product-listing")]//div[@data-item-id]')
    for prod in prods:
        name = prod.xpath('.//div[contains(@class, "product-name")]/text()').string()
        ssid = prod.xpath('@data-item-id').string()
        url = prod.xpath('.//a/@href').string()

        rating = prod.xpath('.//div[@class="point-rating point-full"]')
        if rating and url and not session.seen(url):
            session.queue(Request(url), process_product, dict(context, name=name, ssid=ssid, url=url))

    next_url = data.xpath('//a[contains(@class, "page-next")]/@href').string()
    if next_url and not session.seen(next_url):
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[@itemprop="brand"]/meta/@content').string()

    mpn = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        if rev.xpath('.//meta[@itemprop="inLanguage"]/@content').string() != 'de-DE':
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//meta[@itemprop="datePublished"]/@content').string()
        if date:
            review.date = date.rsplit(' ', 1)[0]

        # no author

        grade_overall = rev.xpath('count(.//div[@class="point-rating point-full"])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.xpath('.//p[@class="h5"]//text()').string()
        excerpt = rev.xpath('.//p[@itemprop="description"]//text()').string(multiple=True)
        if excerpt and len(excerpt) > 2:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest(excerpt)

            if not session.seen(review.ssid):
                product.reviews.append(review)

    if product.reviews:
        session.emit(product)
