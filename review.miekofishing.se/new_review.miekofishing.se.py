from agent import *
from models.products import *


XCAT = ['WBY']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.miekofishing.se/', use='curl'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@class="li0 has-ul"]')
    for cat in cats:
        name = cat.xpath('(a|span)//text()').string(multiple=True)

        if name not in XCAT:
            sub_cats = cat.xpath('.//li[contains(@class, "li1")]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('(a|span)//text()').string(multiple=True)

                sub_cats1 = sub_cat.xpath('.//li[contains(@class, "li2")]')
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('(a|span)/text()').string()
                    url = sub_cat1.xpath('a/@href').string()

                    if sub_name1 and url:
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))


# product.category = context['cat'].replace('|Övriga tillbehör', '').replace('|Övrigt', '').replace('|Övriga Spinnare', '').replace('|Övriga skeddrag', '')

def process_prodlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "product-title")]/a')
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '')