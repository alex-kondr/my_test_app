from agent import *
from models.products import *


XCAT = ['Shop by Brand']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.jklondon.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@class="nav-bar__item"]')
    for cat in cats:
        name = cat.xpath('a/text()').string(multiple=True)

        if name not in XCAT:
            sub_cats = cat.xpath('.//div[@class="mega-menu__column"]')
            if sub_cats:
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath('span/text()').string()

                    sub_cats1 = sub_cat.xpath('.//a[contains(@class, "mega-menu__link")]')
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('text()').string()
                        url = sub_cat1.xpath('@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
            else:
                sub_cats = cat.xpath('.//a[contains(@class, "nav-dropdown__link")]')
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath('text()').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('')
