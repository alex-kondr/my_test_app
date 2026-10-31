#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


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


def Request(url):
    url = url.replace("www.verkt%C3%B8y.no", "www.xn--verkty-fya.no")
    url = url.replace("www.verktøy.no", "www.xn--verkty-fya.no")
    r = agent.Request(url, force_charset='utf-8')
    return r


def RequestProds(cat_id, offset):
    url = "https://eucs33v2.ksearchnet.com/cs/v2/search"
    options = """--compressed -X POST -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0' -H 'Accept: */*' -H 'Accept-Language: en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Content-Type: application/json' -H 'Priority: u=1' --data-raw '{"context":{"apiKeys":["klevu-1714119055102414"]},"recordQueries":[{"id":"category-list","typeOfRequest":"CATNAV","settings":{"query":{"categoryPath":\"""" + cat_id + """"},"offset":\"""" + str(offset) + """","limit":24,"typeOfRecords":["KLEVU_PRODUCT"]}}],"suggestions":[]}'"""
    r = agent.Request(url, use='curl', force_charset='utf-8', options='-s -L --insecure '+options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.xn--verkty-fya.no/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//li[@data-level="level-1"]')
    for cat in cats:
        name = cat.xpath('div[contains(@class, "group")]//span//text()').string()

        cats1 = cat.xpath('.//li[@data-level="level-2"]')
        for cat1 in cats1:
            url = cat1.xpath('div[contains(@class, "group")]//a/@href').string()
            cat1_name = cat1.xpath('div[contains(@class, "group")]//a//text()').string(multiple=True)

            subcats = cat1.xpath('.//li[@data-level="level-3"]/div[contains(@class, "group")]/a')
            if subcats:
                for subcat in subcats:
                    url = subcat.xpath('@href').string()
                    subcat_name = subcat.xpath('text()').string()
                    session.queue(Request(url), process_cat_id, dict(cat=name + '|' + cat1_name + '|' + subcat_name))

            else:
                session.queue(Request(url), process_cat_id, dict(cat=name + '|' + cat1_name))


def process_cat_id(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cat_id = data.xpath('''//script[contains(., 'categoryPath: "')]//text()''').string()
    if cat_id:
        cat_id = cat_id.split('categoryPath: "')[-1].split('"')[0]
        session.queue(RequestProds(cat_id, 0), process_prodlist, dict(context, cat_id=cat_id))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods_json = simplejson.loads(data.content)

    prods = prods_json.get('queryResults', [{}])[0].get('records', [])
    for prod in prods:
        name = prod.get('name')
        url = prod.get('url')
        ssid = prod.get('id')
        sku = prod.get('sku')
        brand = prod.get('manufacturer')

        revs_cnt = prod.get('ratingCount')
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url, ssid=ssid, sku=sku, brand=brand))

    prods_cnt = context.get('prods_cnt', prods_json.get('queryResults',[{}])[0].get('meta', {}).get('totalResultsFound'))
    offset = context.get('offset', 0) + 24
    if prods_cnt and int(prods_cnt) > offset:
        session.queue(RequestProds(context['cat_id'], offset), process_prodlist, dict(context, offset=offset))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = dict()
    product['name'] = context['name']
    product['cat'] = context['cat']
    product['url'] = context['url']
    product['brand'] = context.get('brand')
    product['ssid'] = context['ssid']
    product['sku'] = context.get('sku')

    product['mpn'] = data.xpath('//td[contains(@data-th, "produktnummer")]//text()').string()
    product['ean'] = data.xpath('//td[@data-th="EAN/GTIN"]//text()').string()

    trustpilot = data.xpath("//div[@class='trustpilot-widget'][@data-no-reviews='show']").first()
    if trustpilot:
        template_id = trustpilot.xpath("@data-template-id").string()
        business = trustpilot.xpath("@data-businessunit-id").string()
        locale = trustpilot.xpath("@data-locale").string()

        pid = trustpilot.xpath('@data-sku').string()

        if pid and not session.seen(pid):
            revs_url = "https://widget.trustpilot.com/trustbox-data/" + template_id + "?businessUnitId=" + business + "&locale=" + locale + "&sku=" + str(product['sku']) + "&reviewsPerPage=10"
            session.queue(Request(revs_url), process_reviews, dict(product=product, pid=pid, template_id=template_id, business=business, locale=locale, page=1))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.ssid = context['product']['ssid']
    product.category = context['product']['cat']
    product.url = context['product']['url']
    product.manufacturer = context['product'].get('brand')
    product.sku = context['product'].get('sku')

    mpn = context['product'].get('mpn')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = context['product'].get('ean')
    if ean:
        product.add_property(type='id.ean', value=ean)


    resp = simplejson.loads(data.content)
    revs = resp.get('productReviews', {}).get('reviews', [])
    revs_count = 0
    for rev in revs:
        review = Review()
        review.title = rev.get('title')
        review.type = 'user'
        review.url = product.url
        review.ssid = rev['id']

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('consumer', {}).get('displayName')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('stars')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        grades = rev.get('attributeRatings', [])
        for grade in grades:
            name = grade.get('name')
            value = grade.get('rating')
            if name and value:
                review.grades.append(Grade(name=name, value=float(value), best=5.0))

        excerpt = rev.get('content')
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    if revs_count >= 10:
        page = context['page'] + 1
        revs_url = "https://widget.trustpilot.com/trustbox-data/" + context['template_id'] + "?businessUnitId=" + context['business'] + "&locale=" + context['locale'] + "&sku=" + context['pid'] + "&reviewsPerPage=10&page=" + str(page)
        session.queue(Request(revs_url), process_reviews, dict(context, page=page))
