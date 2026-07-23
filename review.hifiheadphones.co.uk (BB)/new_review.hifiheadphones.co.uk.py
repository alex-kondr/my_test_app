from agent import *
from models.products import *
import simplejson
import time
import random


XCAT = ['Brands', 'Open Box Bargain', 'Sale', 'Blog', 'Top picks', 'Latest additions', 'Best selling']


def run(context, session):
    session.queue(Request('https://www.hifiheadphones.co.uk/', use="curl", force_charset='utf-8', max_age=0), process_frontpage, dict())

    # Upsell prods
    session.queue(Request('https://searchserverapi.com/getresults?api_key=7y2h4h6Y1b&startIndex=0&maxResults=250&page=1&collection=upsell-earphones-500', use="curl", force_charset='utf-8', max_age=0), process_prodlist, dict(cat='Earphones'))
    session.queue(Request('https://searchserverapi.com/getresults?api_key=7y2h4h6Y1b&startIndex=0&maxResults=250&page=1&collection=upsell-earphones-150-500', use="curl", force_charset='utf-8', max_age=0), process_prodlist, dict(cat='Earphones'))
    session.queue(Request('https://searchserverapi.com/getresults?api_key=7y2h4h6Y1b&startIndex=0&maxResults=250&page=1&collection=upsell-earphones-100', use="curl", force_charset='utf-8', max_age=0), process_prodlist, dict(cat='Earphones'))


def process_frontpage(data, context, session):
    time.sleep(random.uniform(1, 3))

    cats = data.xpath('//div[@class="header__menu"]//div[contains(@class, "navbar-item")]//a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use="curl", force_charset='utf-8', max_age=0), process_subcategory, dict(cat=name))


def process_subcategory(data, context, session):
    time.sleep(random.uniform(1, 3))

    subcats = data.xpath('//div[contains(@class, "grid")]/div[contains(@class, "list-collection")]')
    for subcat in subcats:
        name = subcat.xpath('.//span[@class="title"]/text()').string().capitalize()
        cat_id = subcat.xpath('.//a[contains(@class, "collection-info")]/@href').string().split('collections/')[-1]
        url = 'https://searchserverapi.com/getresults?api_key=7y2h4h6Y1b&startIndex=0&maxResults=250&page=1&collection=' + cat_id

        if name not in XCAT:
            session.queue(Request(url, use="curl", force_charset='utf-8', max_age=0), process_prodlist, dict(cat=context['cat']+'|'+name, cat_id=cat_id))


def process_prodlist(data, context, session):
    time.sleep(random.uniform(1, 3))

    prodlist_json = simplejson.loads(data.content)

    prods = prodlist_json.get('items', [])
    for prod in prods:
        url = 'https://www.hifiheadphones.co.uk/products/' + prod['link'].split('/')[-1]
        session.queue(Request(url, use="curl", force_charset='utf-8'), process_product, dict(context, url=url))

    prods_cnt = context.get('prods_cnt', prodlist_json.get('totalItems'))
    offset = context.get('offset', 0) + 250
    if offset < int(prods_cnt):
        next_page = context.get('page', 1) + 1
        next_url = 'https://searchserverapi.com/getresults?api_key=7y2h4h6Y1b&startIndex={}&maxResults=250&page={}&collection={}'.format(offset, next_page, context['cat_id'])
        session.queue(Request(next_url, use="curl", force_charset='utf-8', max_age=0), process_prodlist, dict(context, prods_cnt=prods_cnt, offset=offset, page=next_page))


def process_product(data, context, session):
    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = data.xpath('//h1[@class="product_name title"]//span/text()').string()
    product.url = context['url']
    product.ssid = data.xpath('//div[@class="jdgm-widget jdgm-preview-badge"]/@data-id').string()
    product.category = context['cat']

    prod_json = data.xpath('''//script[contains(., '"@type": "Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')
        product.sku = prod_json.get('sku')

        ean = prod_json.get('gtin12') or prod_json.get('gtin13')
        if ean and str(ean).isdigit() and len(str(ean)) > 10:
            product.add_property(type='id.ean', value=str(ean))

    revs = data.xpath('//span[@class="jdgm-prev-badge__text"][not(contains(., "No"))]/text()').string()
    if revs and int(revs.split()[0]) > 0:
        revs_url = 'https://judge.me/reviews/reviews_for_widget?url=hifi-headphones.myshopify.com&shop_domain=hifi-headphones.myshopify.com&platform=shopify&page=1&per_page=10&product_id={}'.format(product.ssid)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    time.sleep(random.uniform(1, 3))

    product = context["product"]

    json = simplejson.loads(data.content)
    html = data.parse_fragment(json["html"])

    revs = html.xpath("//div[@class='jdgm-rev jdgm-divider-top']")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath(".//@data-review-id").string()

        date = rev.xpath(".//span[@class='jdgm-rev__timestamp jdgm-spinner']/@data-content").string()
        if date:
            review.date = date.split(" ")[0]

        author = rev.xpath(".//span[@class='jdgm-rev__author']/text()").string()
        if author and author != 'null':
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath(".//span/@data-score").string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('@data-verified-buyer').string()
        if is_verified == 'true':
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.xpath('@data-thumb-up-count').string()
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('@data-thumb-down-count').string()
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.xpath(".//b[@class='jdgm-rev__title']//text()").string()
        excerpt = rev.xpath(".//div[@class='jdgm-rev__body']//text()").string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    next_url = html.xpath('//a[@rel="next"]')
    if next_url:
        next_page = context.get("page", 1) + 1
        revs_url = 'https://judge.me/reviews/reviews_for_widget?url=hifi-headphones.myshopify.com&shop_domain=hifi-headphones.myshopify.com&platform=shopify&page={}&per_page=10&product_id={}'.format(next_page, product.ssid)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, page=next_page))

    elif product.reviews:
        session.emit(product)
