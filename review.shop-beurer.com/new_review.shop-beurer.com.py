from agent import *
from models.products import *
import simplejson


XCAT = ['Sale', 'Support', 'Learn More']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=9000)]
    session.queue(Request('https://www.shop-beurer.com/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@aria-label="New Megamenu"]/li[not(a)]')
    for cat in cats:
        name = cat.xpath('text()').string(multiple=True)

        if name not in XCAT:
            sub_cats = cat.xpath('ul//a')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//h2[contains(@class, "title")]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div[@id]/@data-id').string()
    product.category = context['cat']

    prod_json = data.xpath('''//script[contains(text(), '"@type": "Product"')]//text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')

        mpn = prod_json.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('mpn')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_cnt = data.xpath('//div/@data-number-of-reviews').string()
    if revs_cnt and int(revs_cnt) > 0:
        revs_url = 'https://api.judge.me/reviews/reviews_for_widget?url=shop-beurer.myshopify.com&shop_domain=shop-beurer.myshopify.com&platform=shopify&page=1&per_page=5&product_id={}'.format(product.ssid)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs_html = data.parse_fragment(revs_json.get('html'))
    revs = revs_html.xpath('//div[@data-review-id]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@data-review-id').string()

        date = rev.xpath('.//span/@data-content').string()
        if date:
            review.date = date.split()[0]

        author = rev.xpath('.//span[@class="jdgm-rev__author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span/@data-score').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('@data-verified-buyer').string()
        if is_verified and is_verified == 'true':
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.xpath('.//b[@class="jdgm-rev__title"]/text()').string()
        excerpt = rev.xpath('.//div[@class="jdgm-rev__body"]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    revs_cnt = revs_json.get('total_count')
    offset = context.get('offset', 0) + 5
    if offset < revs_cnt:
        next_page  = context.get('page', 1) + 1
        next_url = 'https://api.judge.me/reviews/reviews_for_widget?url=shop-beurer.myshopify.com&shop_domain=shop-beurer.myshopify.com&platform=shopify&page={page}&per_page=5&product_id={ssid}'.format(page=next_page, ssid=product.ssid)
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
