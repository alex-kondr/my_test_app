from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers=[SessionBreak(max_requests=10000)]
    session.queue(Request('https://id.nl/'), process_frontpage, {})


def process_fronpage(data, context, session):
    cats = data.xpath('//div[@class="flex flex-row justify-start w-full"]/a')
    sub_cats = data.xpath('//div[@class="hidden navigation_navigation-sub-menu__V_oxX"]')
    for cat, sub_cat in zip(cats, sub_cats):
        name = cat.xpath('.//span/text()').string()
        print('name=', name)
        sub_cats_ = sub_cat.xpath('.//div[contains(@class, "flex-1")]')

        for sub_cat in sub_cats_:
            sub_name = sub_cat.xpath('.//span/text()').string()
            sub_url = sub_cat.xpath('div/a/@href').string()

            sub_cats2 = sub_cat.xpath('.//li')
            for sub_cat2 in sub_cats2:
                sub_name2 = sub_cat2.xpath('.//div/text()').string()
                print('cat=', name + '|' + sub_name + '|' + sub_name2)
                url = sub_cat2.xpath('a/@href').string()
                session.queue(Request(url + '?filter=Reviews'), process_revlist, dict(cat=name + '|' + sub_name + '|' + sub_name2))

            session.queue(Request(sub_url + '?filter=Reviews'), process_revlist, dict(cat=name + '|' + sub_name))