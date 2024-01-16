from agent import *
from models.products import *
import PyPDF2


def run(context, session):
    # session.queue(Request('https://www.labelident.com/'), process_frontpage, dict())
    session.queue(Request('https://content.labelident.com/godex_g500_druckertest_5b5c413b302eb2fab71ee9645e8ce6c6.pdf'), process_product, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@class="uxnav-main-prod"]/li')
    for cat in cats:
        name = cat.xpath('.//div[@class="add-on-ux-menu category-title level0 submenu"]//span/text()').string()

        sub_cats = cat.xpath('.//ul[@class="level0 submenu"]/li')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('(a|span)//text()').string(multiple=True)

            sub_cats1 = sub_cat.xpath('.//ul[@class="level1 submenu"]/li')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('.//text()').string(multiple=True)
                url = sub_cat1.xpath('a/@href').string()

                if url:
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
            else:
                url = sub_cat.xpath('a/@href').string()
                if url:
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))
        else:
            url = cat.xpath('.//div[@class="add-on-ux-menu category-title level0 submenu"]/a/@href').string()
            if url:
                session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    pass


def process_product(data, context, session):
    pass
