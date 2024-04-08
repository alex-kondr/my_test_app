from agent import *
from models.products import *


XCAT = ['Laufen', 'WEITERE', 'NEUHEITEN', 'BESTSELLER', 'Sale', 'Bestseller']


def run(context, session):
    session.queue(Request('https://shop4runners.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[a[@class="lg:hidden w-full h-full flex items-center justify-center cursor-pointer"]]')
    for cat in cats:
        name = cat.xpath('div[@class="lg:p-3"]/text()').string()

        sub_cats = cat.xpath('.//div[contains(@class, "category-item nav-item-wrapper nav-item-wrapper--and-text bg-white bg-white border-b lg:border-b-0 lg:inline-block itm-")]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('div/div/a[@class="nav-item__title uppercase no-underline"]/text()').string()

            if sub_name and sub_name not in XCAT:
                sub_cats1 = sub_cat.xpath('.//div[@class="category-item nav-item-wrapper nav-item-wrapper--and-text bg-white bg-white border-b lg:border-b-0 lg:inline-block"]|.//a[contains(@class, "nav-item__title lg:hover:bg-neutral-90")]')
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('(.//div[@class="nav-item__title uppercase"]/text()|text())[normalize-space()]').string()

                    if sub_name1 not in XCAT:
                        sub_cats2 = sub_cat1.xpath('.//div[@class="nav-item nav-item__link"]/a')

                        if sub_cats2:
                            for sub_cat2 in sub_cats2:
                                sub_name2 = sub_cat2.xpath('text()').string()
                                url = sub_cat2.xpath('@href').string()
                                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1 + '|' + sub_name2))
                        else:
                            url = sub_cat1.xpath('@href').string()
                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))

                else:
                    url = sub_cat.xpath('div/div/a[@class="nav-item__title uppercase no-underline"]/@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-info")]')
    for prod in prods:
        name = prod.xpath('.//a[@class="product-item-link"]//text()[normalize-space()]').string(multiple=True)
        url = prod.xpath('.//a[@class="product-item-link"]/@href').string()

        rating = prod.xpath('.//div[@class="rating-number ml-2 text-md"]/span/text()').string()
        if rating and float(rating) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))
