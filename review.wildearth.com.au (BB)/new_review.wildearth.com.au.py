#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ['Brands', 'Popular Brands']


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


def RequestProds(base_url, page):
    url = 'https://cxtlbw.a.searchspring.io/api/search/category.json?siteId=cxtlbw&page={page}&redirectResponse=full&beacon=true&ajaxCatalog=Snap&resultsFormat=native'.format(page=page)
    if '#/' in base_url:
        base_url, prods_filter = base_url.split('#/')
        prods_filter = prods_filter.replace('filter:', 'filter.').replace(':', '=').replace('/', '&')
        url += '&' + prods_filter

    cats = '%3E'.join([cat.title() for cat in base_url.split('shop/')[-1].split('/')])
    url += '&bgfilter.ss_category_hierarchy=All%20Products%3E' + cats

    r = agent.Request(url, force_charset='utf-8')
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

    cats = data.xpath('//nav[@role="navigation"]/div/ul/li')
    for cat in cats:
        name = cat.xpath('a//text()').string()

        if name and name not in XCAT:
            subcats = cat.xpath('.//ul[contains(@class, "list")]/li[not(contains(@class, "parent-item"))]')

            for subcat in subcats:
                cat1_name = subcat.xpath('(preceding-sibling::li[contains(@class, "parent-item")])[last()]/a//text()').string()

                if cat1_name != name or not cat1_name.startswith('All ') or cat1_name not in XCAT:
                    subcat_name = subcat.xpath('a/text()').string()
                    url = subcat.xpath('a/@href').string()
                    session.queue(RequestProds(url, 1), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name, cat_url=url))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    try:
        prods_json = simplejson.loads(data.content)
    except:
        prods_json = {}

    prods = prods_json.get('results', [])
    for prod in prods:
        pr = dict()
        pr['name'] = prod.get('name')
        pr['url'] = prod.get('url')
        pr['ssid'] = prod.get('id')
        pr['category'] = context['cat'].replace('Other|', '').replace('Shop by ', '')
        pr['manufacturer'] = prod.get('brand')
        pr['mpn'] = prod.get('sku')

        revs_cnt = prod.get('ratingCount')
        if revs_cnt and int(revs_cnt) > 0 and not session.seen(pr['ssid']):
            session.queue(Request(pr['url']), process_product, dict(product=pr, revs_cnt=int(revs_cnt)))

    prods_cnt = context.get('prods_cnt', prods_json.get('pagination', {}).get('totalResults', 0))
    offset = context.get('offset', 0) + 48
    if prods_cnt and offset < int(prods_cnt):
        next_page = context.get('page', 1) + 1
        session.queue(RequestProds(context['cat_url'], next_page), process_prodlist, dict(context, prods_cnt=prods_cnt, offset=offset, page=next_page))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    context['product']['sku'] = data.xpath('//div/@data-product-id').string()
    context['product']['ean'] = data.xpath('//meta[@itemprop="mpn"]/@content').string()

    session.queue(RequestRevs(context['product']['sku'], 1), process_reviews, dict(context))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']
    product.sku = context['product']['sku']
    product.category = context['product']['category']
    product.manufacturer = context['product']['manufacturer']

    mpn = context['product']['mpn']
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = context['product']['ean']
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    new_data = data.parse_fragment(revs_json.get('reviewsData'))

    revs = new_data.xpath('//div[contains(@class, "custom-review-list")]/div/div/div')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//span[@class="review-date"]//text()').string()

        author = rev.xpath('h1[@itemprop="author"]/span[@itemprop="name"]/text()').string()
        if author and 'anonym' not in author.lower():
            review.authors.append(Person(name=author, ssid=author))
        else:
            author = None

        grade_overall = rev.xpath('.//meta[@itemprop="ratingValue"]/@content').string()
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//div[@class="label-text"][contains(., "Verified")]')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.xpath('.//p[@itemprop="reviewBody"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            ssid = rev.xpath('div/@id').string()
            if ssid:
                review.ssid = ssid.replace('stacktome', '')
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    offset = context.get('offset', 0) + 20
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        session.queue(RequestRevs(product.sku, next_page), process_reviews, dict(context, offset=offset, page=next_page))
