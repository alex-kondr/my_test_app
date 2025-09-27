from agent import *
from models.products import *
import simplejson
import re


XCAT = ['VERKAUF', 'SALE']


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


def get_token(data, context, session):
    resp = simplejson.loads(data.content)
    token = resp.get('token')
    return token


def run(context, session):
    session.queue(Request("https://store.blackview.hk", use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@data-menu-nav]/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "t4s-main-collection-page")]//h3/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    # Loaded all prods


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = 'Blackview'
    product.ssid = data.xpath('//div/@data-gw-product-id').string()

    prod_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        mpn = prod_json.get("sku")
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn.strip('_'))

        ean = prod_json.get("mpn")
        if ean:
            product.add_property(type='id.ean', value=str(ean))

    prod_info = data.xpath('//script[@id="viewed_product"]/text()').string()
    if prod_info and 'rating_count' in prod_info:
        revs_cnt = prod_info.split('"rating_count":', 1)[-1].split('};')[0]
        if revs_cnt and int(revs_cnt) > 0:
            api_url = 'https://store.blackview.hk/apps/ssw/storefront-api/storefront-authentication-service/v2/auth/proxy?x-gw-current-app=default&x-gw-token-strategy=growave&shop=blackview-store.myshopify.com'
            options = """--data-raw '{"token":""}'"""
            token = session.do(Request(api_url, use='curl', options=options, force_charset='utf-8', max_age=0), get_token, {})

            revs_url = 'https://store.blackview.hk/apps/ssw/storefront-api/reviews-storefront/v2/review/getReviewList?x-gw-current-app=default&designMode=false&productId={0}&offset=0&perPage=5&token={1}&x-gw-token-strategy=growave'.format(product.ssid, token)
            session.do(Request(revs_url, use='curl', max_age=0, force_charset='utf-8'), process_reviews, dict(product=product, token=token))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('items', [])
    for rev in revs:
        if rev.get('isPublished') == False:
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.title = rev.get('title')
        review.ssid = str(rev.get('id'))

        author = rev.get('customer', {}).get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        is_verified = rev.get('customer', {}).get('isVerifiedBuyer')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('votes')
        if hlp_yes and hlp_yes > 0:
            review.add_property(type='helpful_votes', value=hlp_yes)

        grade_overall = rev.get('rating')
        if grade_overall and grade_overall > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('body')
        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', ' ').strip(' +')
            if excerpt:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    revs_cnt = revs_json.get('totalCount')
    if offset < revs_cnt:
        token = context['token']
        revs_url = 'https://store.blackview.hk/apps/ssw/storefront-api/reviews-storefront/v2/review/getReviewList?x-gw-current-app=default&designMode=false&productId={0}&offset={1}&perPage=5&token={2}&x-gw-token-strategy=growave'.format(product.ssid, offset, token)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, offset=offset))

    elif product.reviews:
        session.emit(product)
