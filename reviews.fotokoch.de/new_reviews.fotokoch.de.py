from agent import  *
from models.products import *


XCAT = ['Second Hand', 'AREA', 'Aktionen %', 'Workshops', 'Blog', 'alle', '+ weitere']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.fotokoch.de/index.html'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[contains(@class, "checkboxhack_nav_more item_") and div[contains(@class, "checkboxhack_nav_more")]]')
    for cat in cats:
        name = cat.xpath('span[@class="nav_backward"]/span/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('div[contains(@class, "checkboxhack_nav_more")]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('span[@class="nav_backward"]/span/text()').string()

                sub_cats1 = sub_cat.xpath('a[@class="navi"]')
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('text()').string()

                    if sub_name1 not in XCAT:
                        url = sub_cat.xpath('@href').string()
                        session.queue(Request(url + '?listenlimit=0,50'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                else:
                    url = sub_cat.xpath('a[@class="nav_desktop_level_2 navi"]/@href').string()
                    session.queue(Request(url + '?listenlimit=0,50'), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="flex-masonry"]')
    for prod in prods:
        name = prod.xpath('.//div[@class="_b"]//a/@title').string()
        url = prod.xpath('.//div[@class="_b"]//a/@href').string()

        revs_cnt = prod.xpath('.//div[@class="_c"]//span[not(@class)]/text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = data.xpath('//head[meta[@itemprop="sku"]]/meta[@itemprop="name"]/@content').string()
    product.ssid = data.xpath('//meta[@itemprop="sku"]/@content').string()
    product.sku = product.ssid

    mpn = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//div[contains(., "EAN")]/following-sibling::div[@class="_td last"]//span/text()').string()
    if ean and ean.isdigit() and len(ean) == 13:
        product.add_property(type='id.ean')

    context['product'] = product

    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
