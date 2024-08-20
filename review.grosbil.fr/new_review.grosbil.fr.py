from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('http://www.grosbill.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//fieldset[.//li]')
    for cat in cats:
        name = cat.xpath('p//text()').string(multiple=True)

        sub_cats = cat.xpath('.//ul')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('li[@class]//span//text()').string(multiple=True)

            sub_cats1 = sub_cat.xpath('li[not(@class)]')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('a//text()').string(multiple=True)
                url = sub_cat1.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="grb__liste-produit__liste__produit__information__container" and .//p[contains(., " avis)")]]')
    for prod in prods:
        name = prod.xpath('.//h2//text()').string(multiple=True)
        url = prod.xpath('.//a/@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    pass
