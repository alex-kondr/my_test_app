#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ["Golden Friday", "SALE", "Gifts", "Brands", "UAE", "Top Brands", "Offers", "Explore", "View All", "Top Picks", 'Get Inspired', 'Sale']


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    meta_re = re.compile('<ul class="filter-available".*?</ul>', re.DOTALL)
    incontent = file(data.content_file).read()
    outcontent = meta_re.sub("", incontent)
    outcontent = outcontent.replace(' xmlns=', ' abcd=')
    outcontent = outcontent.replace(' xmlns:', ' abcd:')
    outcontent = outcontent.replace('ns0:', '')
    outcontent = outcontent.replace('<!-------', '<!--')
    outcontent = outcontent.replace('----->', '-->')
    # print len(incontent), len(outcontent)
    file(tmp, "w").write(outcontent)
    os.rename(tmp, data.content_file)


def RequestRevs(ssid, page, sku):
    url = 'https://stamped.io/api/widget?productId={ssid}&productSKU={sku}&page={page}&apiKey=pubkey-OX50u46uD98Z57TYHq0amWyKh04j7J&sId=206203&take=5&storeUrl=www.jashanmal.com'.format(ssid=ssid, page=page, sku=sku)
    r = Request(url)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.jashanmal.com'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('(//nav/ul[@role="list"])[1]/li')
    for cat in cats:
        name = cat.xpath('.//summary[contains(@class, "header__menu-item")]//text()').string(multiple=True)

        if name not in XCAT:
            cats1 = cat.xpath('.//div[contains(@id, "MegaMenu")]/ul/li')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a//text()').string()

                if cat1_name not in XCAT:
                    subcats = cat1.xpath('ul/li/a')

                    for subcat in subcats:
                        subcat_name = subcat.xpath('text()').string()
                        url = subcat.xpath('@href').string()

                        if subcat_name not in XCAT:
                            session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    try:
        prods_json = data.xpath('''//script[contains(., '"@type": "BreadcrumbList"')]/text()''').string()
        prods_json = simplejson.loads(prods_json).get('@graph', [])
        for info in prods_json:
            if info.get('@type') == 'CollectionPage':
                prods = info.get('mainEntity', {}).get('itemListElement', [])
                break
    except:
        prods = []

    for prod in prods:
        name = prod.get('name')
        url = prod.get('url')
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        next_url = 'https://www.jashanmal.com' + next_url
        if not session.seen(next_url):
            session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    pr = dict()
    pr['name'] = context['name'].replace('â€“', '-')
    pr['url'] = context['url']
    pr['ssid'] = data.xpath('//product-info/@data-product-id').string()
    pr['sku'] = data.xpath('//tr[contains(th, "SKU:")]/td//text()').string()
    pr['category'] = context['cat']
    pr['manufacturer'] = data.xpath('//a[@class="product__vendor"]/text()').string()
    pr['mpn'] = data.xpath('//tr[contains(th, "Model Number:")]/td/text()').string()

    try:
        prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type": "Product"')]//text()''').string())
        pr['ean'] = prod_json.get('hasVariant', [{}])[0].get('gtin')
    except:
        pass

    if pr['ssid'] and not session.seen(pr['ssid']):
        session.queue(RequestRevs(pr['ssid'], 1, pr['sku']), process_reviews, dict(product=pr))


def process_reviews(data: Response, context: dict[str, str], session: Session):
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

    ean = context['product'].get('ean')
    if ean and str(ean).isdigit() and len(str(ean)) > 10:
        product.add_property(type='id.ean', value=ean)

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs_html = revs_json.get('widget', '')
    revs_html = data.parse_fragment(revs_html)

    revs = revs_html.xpath("//div[@class='stamped-review']")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath(".//div[@class='created']//text()").string()

        author = rev.xpath(".//strong[@class='author']//text()").string()
        if author and 'anonym' not in author:
            review.authors.append(Person(name=author, ssid=author))
        else:
            author = None

        grade_overall = rev.xpath("@data-rating").string()
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        if not grade_overall:
            grade_overall = rev.xpath("count(.//i[@class='stamped-fa stamped-fa-star'])")
            if float(grade_overall) > 0:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath("@data-verified").string()
        if is_verified and is_verified == "buyer":
            review.add_property(type='is_verified_buyer', value=True)

        review.title = rev.xpath(".//div[@class='stamped-review-header-title']//text()").string()
        excerpt = rev.xpath(".//p[@class='stamped-review-content-body']//text()").string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            ssid = rev.xpath("@id").string()
            if ssid:
                review.ssid = ssid.split('-')[-1]
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    revs_cnt = context.get('revs_cnt', revs_json.get('count', 0))
    offset = context.get('offset', 0) + 5
    if offset < int(revs_cnt):
        next_page = context.get('page', 1) + 1
        session.queue(RequestRevs(product.ssid, next_page, product.sku), process_reviews, dict(context, page=next_page, offset=offset, revs_cnt=revs_cnt))
