#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ['Branduri de TOP', 'Resigilate', 'Alege produsul potrivit:', 'Servicii Instalare - Montaj', 'Montare electrocasnice', 'Montare aer conditionat']


def Request(url):
    r = agent.Request(url, proxies=['eu'], force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.emag.ro'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//li[contains(@class, "megamenu-list-department")]/a')
    for cat in cats:
        name = cat.xpath('.//span[contains(@class, "department-name")]//text() | .//text()').string(multiple=True)
        url = cat.xpath('@href').string()

        if url and name and name not in XCAT and not session.seen(url):
            session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//ul[contains(@class, "emg-aside-links") or contains(@class, "sidebar-tree")]//li/a | //div[contains(@class, "sidebar")]//ul//li/a')
    for cat in cats:
        subcat_name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()

        if url and subcat_name and subcat_name not in XCAT and not url.startswith(('/label/', '/shop/', '/shopping-assistant/', '/lps/', '/resigilate/')) and not session.seen(url):
            cat_path = context['cat'] + '|' + subcat_name
            session.queue(Request(url), process_catlist, dict(cat=cat_path))

    if not cats:
        process_prodlist(data, context, session)


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//a[contains(@class, "product-title")]/@href').strings()
    for url in prods:
        if url and not session.seen(url):
            session.queue(Request(url), process_product, dict(context, url=url))

    next_url = data.xpath('//a[@aria-label="Next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def remove_emoji(string):
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002500-\U00002BEF"  # chinese char
                               u"\U00002702-\U000027B0"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


def process_product(data: Response, context: dict[str, str], session: Session):
    info_str = data.xpath('//script[contains(., \'"@type": "Product"\')]//text()').string()
    if not info_str:
        return

    try:
        info = simplejson.loads(info_str)
    except:
        return

    revs_count = info.get('aggregateRating', {}).get('reviewCount', 0)
    if not revs_count or int(revs_count) == 0:
        return

    product = dict()
    product['category'] = context['cat']
    product['name'] = info.get('name')
    product['url'] = info.get('url')
    product['sku'] = info.get('sku')
    product['ssid'] = product['sku']
    product['description'] = info.get('description')

    brand = info.get('brand') or {}
    product['manufacturer'] = brand.get('name')

    mpn = data.xpath('//span[contains(@class, "product-code-display")]//text()').string()
    if mpn:
        product['mpn'] = mpn.replace('Cod produs:', '').strip()

    revs_urn = product['url'].split('emag.ro/')[-1]
    revs_url = 'https://www.emag.ro/product-feedback/' + revs_urn + 'reviews/list?token=&page[offset]=0&page[limit]=20&sort[votes]=desc'
    session.queue(Request(revs_url), process_reviews, dict(product=product, revs_urn=revs_urn, offset=0, limit=20))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.category = context['product']['category']
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.sku = context['product']['sku']
    product.ssid = context['product']['ssid']
    product.description = context['product']['description']
    product.manufacturer = context['product']['manufacturer']

    if context['product'].get('mpn'):
        product.add_property(type='id.manufacturer', value=context['product']['mpn'])

    try:
        resp = simplejson.loads(data.content)
    except:
        return

    revs = resp.get('reviews', {}).get('items', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id', ''))
        review.title = rev.get('title')

        date = rev.get('created')
        if date:
            review.date = date.split('T')[0]

        user = rev.get('user') or {}
        author_name = user.get('name')
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = rev.get('rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        if rev.get('is_buyer') or rev.get('is_verified'):
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.get('content_no_tags') or rev.get('content')
        if excerpt:
            excerpt = remove_emoji(excerpt).strip()
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)
                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    limit = context.get('limit', 20)
    if len(revs) >= limit:
        offset = context.get('offset', 0) + limit
        revs_url = 'https://www.emag.ro/product-feedback/' + context['revs_urn'] + 'reviews/list?token=&page[offset]=' + str(offset) + '&page[limit]=' + str(limit) + '&sort[votes]=desc'
        session.queue(Request(revs_url), process_reviews, dict(context, offset=offset))
