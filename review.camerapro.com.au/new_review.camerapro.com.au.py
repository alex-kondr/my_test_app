from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.camerapro.com.au/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "level0")]')
    for cat in cats:
        name = cat.xpath('a/span/text()').string()

        sub_cats = cat.xpath('.//span[contains(., "Shop By Category")]/following-sibling::ul/li[contains(@class, "level1")]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('a/span/text()').string()

            sub_cats1 = sub_cat.xpath('.//ul[@class="category-links"]/li/a')
            if sub_cats1:
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('span/text()').string()
                    url = sub_cat1.xpath('@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
            else:
                url = sub_cat.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//li[@class="item product product-item"]')
    for prod in prods:
        name = prod.xpath('.//strong[contains(@class, "product-item-name")]/a/text()').string()
        url = prod.xpath('.//strong[contains(@class, "product-item-name")]/a/@href').string()

        revs = prod.xpath('.//a[@class="action view"]/text()').string()
        if revs:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@class="action next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))
