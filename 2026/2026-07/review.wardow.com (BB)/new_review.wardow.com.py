from agent import *
from models.products import *
import simplejson
import time
import random
import re


XCAT = ['New', 'Brands', 'Sale %', 'Inspiration']


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


def RequestProds(cat_id, page):
    options = """--compressed -X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Content-Type: application/json' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: cross-site' --data-raw '{"pageSize":48,"page":""" + str(page) + ''',"placement":"projects/retail-catalog-488412/locations/global/catalogs/default_catalog/servingConfigs/default_search","query":"","filters":[{"field":"attributes.rcc_collection_id","value":["'''+ cat_id + """\"]}],"filterFields":["brands","attributes.series","colorFamilies","price","attributes.product_type","materials","genders","patterns","attributes.occasion","attributes.discount","attributes.laptop","attributes.luggage_type","attributes.luggage_size","attributes.rollsystem","attributes.capacity_group","attributes.weight_group","attributes.sustainability"],"visitorId":"46c71c91-2754-4d78-9f8e-2ac3cf80ddcb","languageCode":"en-DE"}'"""
    url = 'https://storefront.retailconnect.app/v1/search'
    r = Request(url, use='curl', options=options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.wardow.com/en/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(2, 5))

    cats = data.xpath('//li[contains(@class, "menu-list")]')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        if name and name not in XCAT:
            subcats = cat.xpath('.//li[div/a/span[contains(text(), "Categories")]]/div/ul/li/a[not(contains(., "Show all"))]')
            for subcat in subcats:
                subcat_name = subcat.xpath('.//text()').string(multiple=True)
                url = subcat.xpath('@href').string()
                session.queue(Request(url), process_category, dict(cat=name+'|'+subcat_name))
            else:
                url = cat.xpath('a/@href').string()
                session.queue(Request(url), process_category, dict(cat=name))


def process_category(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(2, 5))

    cat_id = data.xpath('//div/@data-collection-id').string()
    if cat_id:
        session.do(RequestProds(cat_id, 1), process_prodlist, dict(context, cat_id=cat_id))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(2, 5))

    try:
        prods_json = simplejson.loads(data.content).get('value', {})
    except:
        prods_json = {}

    prods = prods_json.get('results', [])
    for prod in prods:
        product = Product()
        product.name = prod.get('product', {}).get('title')
        product.url = prod.get('product', {}).get('uri')
        product.ssid = str(prod.get('id'))
        product.sku = prod.get('product', {}).get('variants', [{}])[0].get('id')
        product.category = context['cat']
        product.manufacturer = prod.get('product', {}).get('brands', [''])[0]

        revs_cnt = prod.get('product', {}).get('variants', [{}])[0].get('rating', {}).get('ratingCount', 0)
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(product.url), process_product, dict(product=product, revs_cnt=int(revs_cnt)))

    prods_cnt = context.get('prods_cnt', prods_json.get('pagination', {}).get('totalSize', 0))
    offset = context.get('offset', 0) + 48
    if offset < prods_cnt:
        next_page = context.get('page', 1) + 1
        session.do(RequestProds(context['cat_id'], next_page), process_prodlist, dict(context, page=next_page, offset=offset, prods_cnt=prods_cnt))


def process_product(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(2, 5))

    product = context['product']

    mpn = data.xpath('//strong[contains(text(), "Model number:")]/following-sibling::text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    prod_json = data.xpath("""//script[contains(., '"@type":"Product"')]/text()""").string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        ean = prod_json.get('gtin')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_url = 'https://api-cdn.yotpo.com/v3/storefront/store/juPydjP7F5lNKZqAAkBS8XjnFJaiWnVEaQq9xmxN/product/{}/reviews?page=1&perPage=5'.format(product.ssid)
    session.do(Request(revs_url, max_age=0), process_reviews, dict(context, product=product))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(2, 5))

    product = context['product']

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('reviews', [])
    for rev in revs:
        if rev.get('language') != 'en' or rev.get('syndicationData') or rev.get('groupingData'):
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('user', {}).get('displayName')
        author_ssid = rev.get('user', {}).get('userId')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=str(author_ssid)))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('score')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.get('votesUp')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('votesDown')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        is_verified_buyer = rev.get('verifiedBuyer')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('title')
        excerpt = rev.get('content')
        if excerpt and len(remove_emoji(excerpt).replace('\n', '').strip()) > 2:
            if title:
                review.title = remove_emoji(title).replace('\n', '').strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        revs_url = 'https://api-cdn.yotpo.com/v3/storefront/store/juPydjP7F5lNKZqAAkBS8XjnFJaiWnVEaQq9xmxN/product/{ssid}/reviews?page={page}&perPage=5'.format(ssid=product.ssid, page=next_page)
        session.do(Request(revs_url, max_age=0), process_reviews, dict(context, product=product, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
