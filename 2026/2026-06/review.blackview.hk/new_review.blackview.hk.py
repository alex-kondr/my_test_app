from agent import *
from models.products import *
import simplejson
import re


XCAT = ['VERKAUF', 'SALE', 'Flash Sale', 'Services']


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
    session.browser.use_new_parser = True
    session.queue(Request("https://store.blackview.hk", force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//nav[contains(@class, "header__menu")]/ul/li')
    for cat in cats:
        name = cat.xpath('details/summary/span/span/text()|a//text()').string(multiple=True)

        if name not in XCAT:
            cats1 = cat.xpath('.//div[@class="mega-menu__list"]//div[a]')
            if cats1:
                for cat1 in cats1:
                    cat1_name = cat1.xpath('a/text()').string()

                    subcats = cat1.xpath('ul/li/a')
                    for subcat in subcats:
                        subcat_name = subcat.xpath('.//text()').string(multiple=True)
                        url = subcat.xpath('@href').string().split('?')[0]
                        session.queue(Request(url, force_charset='utf-8'), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
            else:
                url = cat.xpath('a/@href').string().split('?')[0]
                session.queue(Request(url, force_charset='utf-8'), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//h3[contains(@class, "product-card__title")]/a')
    for prod in prods:
        name = prod.xpath('.//text()').string(multiple=True)
        url = prod.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    # Loaded all prods


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div/@data-gw-product-id').string()
    product.category = context['cat']
    product.manufacturer = 'Blackview'

    prod_json = data.xpath('''//script[@type="application/json" and contains(., '"barcode":')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        mpn = prod_json.get("sku")
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn.strip('_'))

        ean = prod_json.get("barcode")
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=str(ean))

    prod_info = data.xpath('//script[@id="viewed_product" and contains(text(), "rating_count")]/text()').string()
    if prod_info:
        revs_cnt = prod_info.split('"rating_count":', 1)[-1].split('};')[0]
        if revs_cnt and int(revs_cnt) > 0:
            api_url = 'https://store.blackview.hk/apps/ssw/storefront-api/storefront-authentication-service/v2/auth/proxy?x-gw-current-app=default&x-gw-token-strategy=growave&shop=blackview-store.myshopify.com'
            options = """--data-raw '{"token":""}'"""
            token = session.do(Request(api_url, use='curl', options=options, force_charset='utf-8', max_age=0), get_token, {})

            revs_url = 'https://store.blackview.hk/apps/ssw/storefront-api/reviews-storefront/v2/review/getReviewList?x-gw-current-app=default&designMode=false&productId={ssid}&offset=0&perPage=5&token={token}&x-gw-token-strategy=growave'.format(ssid=product.ssid, token=token)
            session.do(Request(revs_url, use='curl', max_age=0, force_charset='utf-8'), process_reviews, dict(product=product, token=token, revs_cnt=int(revs_cnt)))


def process_reviews(data, context, session):
    product = context['product']

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('items', [])
    for rev in revs:
        if rev.get('isPublished') == False:
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('customer', {}).get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.get('customer', {}).get('isVerifiedBuyer')
        if is_verified is True:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('votes')
        if hlp_yes and hlp_yes > 0:
            review.add_property(type='helpful_votes', value=hlp_yes)

        title = rev.get('title')
        excerpt = rev.get('body')
        if excerpt and len(remove_emoji(excerpt).replace('\n', '').strip(' +')) > 2:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').strip(' +')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        token = context['token']
        revs_url = 'https://store.blackview.hk/apps/ssw/storefront-api/reviews-storefront/v2/review/getReviewList?x-gw-current-app=default&designMode=false&productId={0}&offset={1}&perPage=5&token={2}&x-gw-token-strategy=growave'.format(product.ssid, offset, token)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, offset=offset))

    elif product.reviews:
        session.emit(product)
