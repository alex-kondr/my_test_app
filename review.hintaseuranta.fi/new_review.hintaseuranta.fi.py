from agent import *
from models.products import *


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('http://hintaseuranta.fi/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="navigation"]/ul/li')
    for cat in cats:
        name = cat.xpath('div/a/text()').string()

        sub_cats = cat.xpath('ul/li/a')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = sub_cat.xpath('@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_catlist, dict(cat=name + '|' + sub_name))


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[contains(@class, "category-list") and h4]')
    for cat in cats:
        name = cat.xpath('h4//text()').string(multiple=True)

        sub_cats = cat.xpath('ul/li/a')
        if sub_cats:
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + name + '|' + sub_name))
        else:
            url = cat.xpath('h4/a/@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + name))

    if not cats:
        process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="item-data"]')
    for prod in prods:
        name = prod.xpath('h4[not(@class)]/a/text()').string()
        url = prod.xpath('h4[not(@class)]/a/@href').string()

        rating = data.xapth('div[@class="item-data-rating"]')
        if rating:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_data = data.xpath('//div[@id="data-values"]//@data-values').string(multiple=True)
    if next_data:
        offset = context.get('offset', 0) + 30
        options = """--compressed -X POST  --data-raw 'vals={data}&skip={offset}&view=&sort=%22popularity+desc%22'""".format(data=next_data, offset=offset)
        session.queue(Request('https://hintaseuranta.fi/facet/listmore', options=options, use='curl', force_charset='utf-8'), process_prodlist, dict(context, offset=offset))


def process_product(data, context, session):
    strip_namespace(data)

    product= Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.sku = product.ssid
    product.category = context['cat']
    
