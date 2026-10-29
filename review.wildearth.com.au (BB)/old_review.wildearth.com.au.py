#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


XCAT = ['Brands']


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


def RequestProds(filters, link, offset):
    url = "https://api-v3.findify.io/v3/smart-collection/shop/" + link
    data_raw = '--data-raw \'{{"user":{{"uid":"QpbWFewJV0fDVUA9","sid":"woqlTL84s2xsBv78","persist":true,"exist":true}},"t_client":1676650606589,"key":"b5d0bba5-839b-46d4-b4e1-57669fc01d47","filters":{filters},"limit":48,"offset":{offset},"slot":"{link}"}}\''.format(filters=filters, link=link, offset=offset)
    options = "--compressed -H 'Content-Type: application/json' -H 'x-key: b5d0bba5-839b-46d4-b4e1-57669fc01d47' " + data_raw
    r = agent.Request(url, use='curl', force_charset='utf-8', options='-s -L --insecure '+options, max_age=0)
    return r


def RequestRevs(pid, page):
    url = "https://services.stacktome.com/api/reviews/v1/templates/313/reviews?apikey=QhG95OtEBPlRcN3ABKexgBCdTUbKZIUl"
    options = """--compressed -X POST -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0' -H 'Accept: */*' -H 'Accept-Language: en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Content-Type: application/json' --data-raw '{"widgetId":313,"apiKey":"QhG95OtEBPlRcN3ABKexgBCdTUbKZIUl","source":"trustpilot","searchInParentLocation":true,"productSku":\"""" + pid + """","timeout":{"timeoutMillis":1000},"reviewType":"product","paging":{"page":""" + str(page) + ""","pageSize":20}}'"""
    r = agent.Request(url, use='curl', force_charset='utf-8', options='-s -L --insecure '+options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.wildearth.com.au/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ul[contains(@class, "nav navbar-nav")]/li[@class="dropdown megamenu-fw"]')
    for cat in cats:
        name = cat.xpath('a//text()').string()

        if name and name not in XCAT:
            subcats = cat.xpath('.//ul[@class="list-unstyled"]/li[not(@class)]/a')

            for subcat in subcats:
                cat1_name = subcat.xpath('preceding::li[@class="parent-item"][1]/a//text()').string()

                if cat1_name == name:
                    continue

                subcat_name = subcat.xpath('text()').string()
                url = subcat.xpath('@href').string()

                filters = []
                filters_list = url.split('filters%5B')[1:]
                for filter_prod in filters_list:
                    fltr = str(filter_prod.split('%5D%5B0%5D=')[0].split('%5D%5B1%5D=')[0])
                    value = str(filter_prod.split('=')[-1].rstrip('&'))
                    custom_filter = {
                        "name":fltr,
                        "type":"text",
                        "values":[{"value":value}]
                        }
                    filters.append(custom_filter)

                link = url.split('shop/')[-1].split('?')[0]

                session.queue(RequestProds(filters, link, 0), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name, link=link, filters=filters))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    try:
        prods_json = simplejson.loads(data.content)
    except:
        return

    prods = prods_json.get('items')
    if not prods:
        return

    for prod in prods:
        name = prod.get('title')
        url = prod.get('product_url')
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    prods_cnt = context.get('prods_cnt', prods_json.get('meta', {}).get('total'))
    offset = context.get('offset', 0) + 48
    if prods_cnt and int(prods_cnt) > offset:
        session.queue(RequestProds(context['filters'], context['link'], offset), process_prodlist, dict(context, prods_cnt=prods_cnt, offset=offset))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = dict()
    product['name'] = context['name']
    product['cat'] = context['cat']
    product['url'] = context['url']
    product['man'] = data.xpath("//meta[@itemprop='name']/@content").string()
    product['ssid'] = data.xpath('//div/@data-product-id').string()
    product['ean'] = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    product['sku'] = data.xpath('//p[@itemprop="sku"]//text()').string()

    if product['ssid'] and not session.seen(product['ssid']):
        session.queue(RequestRevs(product['ssid'], 1), process_reviews, dict(product=product))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['product']['name']
    product.ssid = context['product']['ssid']
    product.url = context['product']['url']
    product.category = context['product']['cat']
    product.manufacturer = context['product'].get('man')

    product.add_property(type='id.manufacturer', value=product.ssid)

    ean = context['product'].get('ean')
    if ean:
        product.add_property(type='id.ean', value=ean)


    revs_json = simplejson.loads(data.content)

    new_data = data.parse_fragment(revs_json.get('reviewsData'))

    revs = new_data.xpath('//div[@class="stacktome_review-element-wrapper custom-review-element-wrapper"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('.//div[@class="stacktome_review-body custom-review-body"]/@id').string()
        review.date = rev.xpath('.//span[@class="review-date"]//text()').string()

        author = rev.xpath('.//h1[@itemprop="author"]/span[@itemprop="name"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//meta[@itemprop="ratingValue"]/@content').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//div[@class="label-text"][contains(., "Verified")]')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.xpath('.//p[@itemprop="reviewBody"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    revs_cnt = context.get('revs_cnt', data.xpath('''//script[contains(text(), '"reviewCount": "')]//text()''').string())
    offset = context.get('offset', 0) + 20
    if revs_cnt and int(revs_cnt.split('"reviewCount": "')[-1].split('"')[0]) > offset:
        next_page = context.get('page', 1) + 1
        session.queue(RequestRevs(product.ssid, next_page), process_reviews, dict(context, revs_cnt=revs_cnt, offset=offset, pae=next_page))
