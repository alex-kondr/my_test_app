from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.dehner.de/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@data-level="1"]')
    for cat in cats:
        name = cat.xpath('div/span[contains(@class, "container--title")]/text()').string()

        sub_cats = cat.xpath('ul[contains(@class, "menu")]/li[div]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('div/span[contains(@class, "container--title")]/text()').string()

            sub_cats1 = sub_cat.xpath('ul[contains(@class, "menu")]/li[div]')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('div/span[contains(@class, "container--title")]/text()').string()
                url = sub_cat1.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-item") and h5]')
    for prod in prods:
        name = prod.xpath('h5/text()').string()
        url = prod.xpath('a/@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//meta[@itemprop="productId"]/@value').string()
    product.sku = product.ssid
    product.category = context['cat']

    manufacturer = data.xpath('//img[contains(@class, "product-logo")]/@src').string()
    if manufacturer:
        product.manufacturer = manufacturer.split('/')[-1].title()

    revs_cnt = data.xpath('//meta[@itemprop="reviewCount"]/@content').string()
    if int(revs_cnt.strip('()')) > 0:
        raise ValueError("!!!!!!!!")
    else:
        print('revs_cnt=', int(revs_cnt.strip('()')))



