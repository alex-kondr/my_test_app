from agent import *
from models.products import *


XCAT = ['Geschenkideen',  'Neuheiten', 'Sale']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.reiterladen24.de/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[div[@class="row navigation-flyout-bar"]]')
    for cat in cats:
        name = cat.xpath('.//a[@class="nav-link"]/@title').string()

        if name not in XCAT:
            sub_cats = cat.xpath('.//div[contains(@class, "is-level-0")]/div')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('.//a[contains(@class, "is-level-0")]/span/text()').string()

                sub_cats1 = sub_cat.xpath('.//div[contains(@class, "is-level-1")]/div')
                if sub_cats1:
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('.//a[contains(@class, "is-level-1")]/span/text()').string()
                        url = sub_cat1.xpath('.//a[contains(@class, "is-level-1")]/@href').string()
                        session.queue(Request(url + '?order=bewertung-desc'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                else:
                    url = sub_cat.xpath('.//a[contains(@class, "is-level-0")]/@href').string()
                    session.queue(Request(url + '?order=bewertung-desc'), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('')
