from agent import *
from models.products import *
import simplejson

XCAT1 = ['Home', 'Shop by Brand', 'Trade account information']
XCAT2 = []


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.jklondon.com/', use='curl', force_charset='utf-8'), process_frontpage, {})


def process_frontpage(data, context, session):
    cats1 = data.xpath('//li[@class="nav-bar__item"]//div[@class="mega-menu__column"]')
    for cat1 in cats1:
        name1 = cat1.xpath('span/text()').string()
        if name1:
            XCAT2.append(name1)
        cats2 = cat1.xpath('.//li/a')
        for cat2 in cats2:
            name2 = cat2.xpath('text()').string()
            url = cat2.xpath('@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_category, dict(cat=name1 + '|' + name2))

    cats1 = data.xpath('//li[@class="nav-bar__item"]/ul[@class="nav-dropdown nav-dropdown--restrict"]/ancestor::li')
    for cat1 in cats1:
        name1 = cat1.xpath('a/text()').string()
        if name1 in XCAT1:
            continue
        if name1:
            XCAT2.append(name1)
        cats2 = cat1.xpath('ul//li/a')
        for cat2 in cats2:
            name2 = cat2.xpath('text()').string()
            url = cat2.xpath('@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_category, dict(cat=name1+'|'+name2))

    cats = data.xpath('//li[@class="nav-bar__item"]')
    for cat in cats:
        name = cat.xpath('a/text()').string()
        if name not in XCAT2:
            url = cat.xpath('a/@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_category, dict(cat=name))


def process_category(data, context, session):
    prods = data.xpath('//div[@class="product-item__info-inner"]')
    for prod in prods:
        name = prod.xpath('a/text()').string()
        ssid = prod.xpath('span/@data-id').string()
        url = prod.xpath('a/@href').string()
        session.queue(Request(url, use='curl'), process_product, dict(context, url=url, name=name, ssid=ssid))

    next_url = data.xpath('//a[@class="pagination__next link"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_category, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[@itemprop="brand"]/@content').string()

    #product.properties.append(ProductProperty(type='id.ean', value=context['ean']))

    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = data.xpath('//input/@data-sku').string()

    mpn = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    if mpn:
        product.properties.append(ProductProperty(type='id.manufacturer', value=mpn))

    revs_url = 'https://productreviews.shopifycdn.com/proxy/v4/reviews/product?callback=productCallback{0}&product_id={0}&version=v4&shop=jklondon.myshopify.com'.format(product.ssid)
    session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    html_str = ''.join(data.content)
    if not html_str:
        return
    html_str = '{"' + html_str.split('({"')[-1][:-1]

    resp = simplejson.loads(html_str)
    revs_json = resp['reviews']
    if not revs_json:
        return
    revs_html = data.parse_fragment(revs_json)

    revs = revs_html.xpath('//div[@class="spr-review-header"]')
    for rev in revs:
        review = Review()
        review.title = rev.xpath('h3[@class="spr-review-header-title"]/text()').string()
        review.type = 'user'
        review.url = product.url

        author_date = rev.xpath('span[@class="spr-review-header-byline"]//text()').string(multiple=True)
        if author_date:
            author_date = author_date.split(' on ')

            author_name = author_date[0]
            review.authors.append(Person(name=author_name, ssid=author_name))

            review.date = author_date[1]

        grade_overall = rev.xpath('span[@class="spr-starratings spr-review-header-starratings"]/@aria-label').string()
        if grade_overall:
            grade_overall = grade_overall.split(' of ')[0]
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('following-sibling::div[@class="spr-review-content"]/p/text()').string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            review.ssid = review.digest()
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
