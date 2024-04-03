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
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                else:
                    url = sub_cat.xpath('a[@class="nav_desktop_level_2 navi"]/@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="flex-masonry"]')
    for prod in prods:
        name = prod.xpath('.//div[@class="_b"]//a/@title').string()
        url = prod.xpath('.//div[@class="_b"]//a/@href').string()

        revs_cnt = prod.xpath('.//div[@class="_c"]//span[not(@class)]/text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))
