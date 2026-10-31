#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ['Black Friday', 'Help & Advice']
XCAT2 = ['all ', 'refurbished', 'deals', 'guide', 'popular', 'brand', 'feature']


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
    r = agent.Request(url, force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.appliancesdirect.co.uk/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//nav[@class="bidmm"]/ul/li')
    for cat in cats:
        name = cat.xpath('a//text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('div/div/ul[h3]') or cat.xpath('div/div/ul/li')

            for cat1 in cats1:
                cat1_name = cat1.xpath('h3//text()').string() or cat1.xpath('a//text()').string()

                if not any(xcat in cat1_name.lower() for xcat in XCAT2):
                    if ' by ' in cat1_name:
                        cat1_name = ''

                    cats2 = cat1.xpath('div/div/ul[h3]') or cat1.xpath('li/a')
                    for cat2 in cats2:
                        url = cat2.xpath('@href').string()
                        cat2_name = cat2.xpath('h3/a//text()').string() or cat2.xpath('text()').string()

                        if not any(xcat in cat2_name.lower() for xcat in XCAT2):
                            subcats = cat2.xpath('li/a[not(@style)]')

                            if subcats and len(subcats) > 1:
                                for subcat in subcats:
                                    url = subcat.xpath('@href').string()
                                    subcat_name = subcat.xpath('text()').string()

                                    if not any(xcat in subcat_name.lower() for xcat in XCAT2):
                                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + cat2_name + '|' + subcat_name))

                            else:
                                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + cat2_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[@id="productList"]/div')
    for prod in prods:
        url = prod.xpath('.//h3/a/@href').string()
        name = prod.xpath('.//h3/a//text()').string()
        ssid = prod.xpath('.//reevoo-badge/@product-id').string()
        mpn = prod.xpath('.//p[contains(., "SKU")]/span/text()').string() or ''

        if ssid and not session.seen(ssid):
            name += ' ' + mpn
            session.queue(Request(url), process_product, dict(context, url=url, name=name, ssid=ssid, mpn=mpn))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url and not session.seen(next_url):
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    pr = dict()
    pr['name'] = context['name']
    pr['category'] = context['cat'].replace('||', '|')
    pr['url'] = context['url']
    pr['ssid'] = context['ssid']
    pr['id.manufacturer'] = context.get('mpn')

    try:
        prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type": "Product"')]//text()''').string())
        pr['manufacturer'] = prod_json.get('brand', {}).get('name')
        pr['id.ean'] = prod_json.get('gtin8')
    except:
        pass

    merchant_identifier = "appliances-direct"
    origin = "www.appliancesdirect.co.uk"

    process_reviews_request(data, dict(product=pr, merchant_identifier=merchant_identifier, origin=origin), session)


def process_reviews_request(data: Response, context: dict[str, str], session: Session):
    page = context.get('page', 1)

    url = 'https://widgets.reevoo.com/api-feefo/api/10/reviews/product'
    url += '?page=' + str(page)
    url += '&page_size=' + str(context.get('page_size', 100))
    url += '&since_period=ALL'
    url += '&full_thread=exclude'
    url += '&unanswered_feedback=include'
    url += '&source=on_page_product_integration'
    url += '&sort=-updated_date'
    url += '&feefo_parameters=include'
    url += '&media=include'
    url += '&merchant_identifier=' + context.get('merchant_identifier')
    url += '&origin=' + context.get('origin')
    url += '&product_sku=' + context['product']['ssid']
    url += '&locale=en_GB'

    session.queue(Request(url), process_reviews_page, dict(context, page=page))


def process_reviews_page(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.ssid = context['product']['ssid']
    product.category = context['product']['category']
    product.url = context['product']['url']
    product.manufacturer = context['product'].get('manufacturer')

    sku = context['product'].get('id.sku')
    if sku:
        product.sku = sku.split(': ')[-1]

    mpn = context['product'].get('id.manufacturer')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = context['product'].get('id.ean')
    if ean:
        product.add_property(type='id.ean', value=ean)


    try:
        resp = simplejson.loads(data.content)
    except:
        return

    revs = resp.get('reviews', [])
    for rev in revs:

        merchant =  rev.get('merchant', {}).get('identifier')
        if merchant and merchant != "appliances-direct":
            continue

        review = Review()
        review.ssid = rev['sale_id']
        review.type = 'user'
        review.url = product.url

        date = rev.get('products', [{}])[0].get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('customer', {}).get('display_name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        rev_content = rev.get('aux', [])
        for key in rev_content:
            if key.get('key') == "purchasedate":
                review.add_property(type='is_verified_buyer', value=True)

        grade_overall = rev.get('products', [{}])[0].get('rating', {}).get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        grades = rev.get('products', [{}])[0].get('attributes', [])
        for grade in grades:
            name = grade.get('name')
            value = grade.get('rating')
            if name and value:
                review.grades.append(Grade(name=name, value=float(value), best=5.0))

        hlp_yes = rev.get('products', [{}])[0].get('helpful_votes')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        excerpt = rev.get('products', [{}])[0].get('review')
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    total_pages = context.get('total_pages', resp.get('summary', {}).get('meta', {}).get('pages'))
    if total_pages and context.get('page') < int(total_pages):
        page = context.get('page') + 1

        url = 'https://widgets.reevoo.com/api-feefo/api/10/reviews/product'
        url += '?page=' + str(page)
        url += '&page_size=' + str(context.get('page_size', 100))
        url += '&since_period=ALL'
        url += '&full_thread=exclude'
        url += '&unanswered_feedback=include'
        url += '&source=on_page_product_integration'
        url += '&sort=-updated_date'
        url += '&feefo_parameters=include'
        url += '&media=include'
        url += '&merchant_identifier=' + context.get('merchant_identifier')
        url += '&origin=' + context.get('origin')
        url += '&product_sku=' + context['product']['ssid']
        url += '&locale=en_GB'

        session.queue(Request(url), process_reviews_page, dict(context, total_pages=total_pages,  page=page))
