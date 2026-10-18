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

    cats = data.xpath('//div[@class="navigation-flyout"]')
    for cat in cats:
        name = cat.xpath('.//div[@class="navigation-flyout-category-link"]/a/@title').string()

        if name not in XCAT:
            cats1 = cat.xpath('.//div[contains(@class, "is-level-0")]/div')
            for cat1 in cats1:
                url = cat1.xpath('a/@href').string()
                cat1_name = cat1.xpath('a/span//text()').string()

                subcats = cat1.xpath('div[contains(@class, "is-level-1")]/div/a')
                if subcats:
                    for subcat in subcats:
                        url = subcat.xpath('@href').string()
                        subcat_name = subcat.xpath('span//text()').string()
                        session.queue(Request(url), process_prodlist, dict(url=url, cat=name + '|' + cat1_name + '|' + subcat_name))

                else:
                    session.queue(Request(url), process_prodlist, dict(url=url, cat=name + '|' + cat1_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "card product-box")]')
    for prod in prods:
        url = prod.xpath('.//a[@class="product-name"]/@href').string()
        if url and not session.seen(url):
            session.queue(Request(url), process_product, dict(context, url=url))

    next_page = data.xpath('//li[@class="page-item page-next"]/input/@value').string()
    if next_page:
        next_url = context['url'] + "?p=" + next_page
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = data.xpath('//h1[@class="product-detail-name"]//text()').string()
    product.category = context['cat']
    product.url = context['url']
    product.manufacturer = data.xpath('//div[@itemprop="brand"]/meta[@itemprop="name"]/@content').string()
    product.ssid = data.xpath('//meta[@itemprop="productID"]/@content').string()


    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//meta[@itemprop="datePublished"]/@content').string()
        if date:
            review.date = " ".join(date.split()[:-1])

        author = rev.xpath('.//div[@itemprop="author"]/meta[@itemprop="name"]/@content').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//div[@class="point-rating point-full"])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.xpath('.//p[@class="h5"]//text()').string()

        excerpt = rev.xpath('.//p[@itemprop="description"]//text()').string(multiple=True)
        if excerpt:

            if title and title.strip(' .') not in excerpt:
                review.title = title

            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
