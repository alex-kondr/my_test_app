#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ['Infos', 'News']


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
    session.queue(Request('https://www.highend-hifi-shop.de/'), process_frontpage, dict())



def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//div[@data-top-navigation-flyout]/div')
    for cat in cats:
        name = cat.xpath('.//div[contains(@class, "navigation-flyout-category-link")]/a/@title').string()

        if name not in XCAT:
            cats1 = cat.xpath('.//div[contains(@class, "is-level-0")]/div')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a/span[@itemprop="name"]//text()').string()

                subcats = cat1.xpath('div[contains(@class, "is-level-1")]/div/a')
                if subcats:
                    for subcat in subcats:
                        url = subcat.xpath('@href').string()
                        subcat_name = subcat.xpath('span[@itemprop="name"]//text()').string()
                        session.queue(Request(url), process_prodlist, dict(url=url, cat=name + '|' + cat1_name + '|' + subcat_name))
                else:
                    url = cat1.xpath('a/@href').string()
                    session.queue(Request(url), process_prodlist, dict(url=url, cat=name + '|' + cat1_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//a[contains(@class, "product-name")]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()

        if url and not session.seen(url):
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@data-focus-id="next"]/@href').string()
    if next_url and not session.seen(next_url):
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[contains(@name, "[id]")]/@value').string()
    product.sku = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    product.category = context['cat'].replace(' / ', '/')
    product.manufacturer = data.xpath('//a[contains(@class, "manufacturer-link")]/@title').string()

    mpn = data.xpath('//span[@itemprop="sku"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 10:
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

        author = rev.xpath('.//div[@itemprop="author"]/meta[@itemprop="name"]/@content').string()
        if author and 'anonym' not in author.lower():
            review.authors.append(Person(name=author, ssid=author))
        else:
            author = None

        grade_overall = rev.xpath('count(.//div[@class="point-rating point-full"])')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.xpath('.//p[contains(@class, "h5")]//text()').string()
        excerpt = rev.xpath('.//p[@itemprop="description"]//text()').string(multiple=True)
        if excerpt:
            if title and title.strip(' .') not in excerpt:
                review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
