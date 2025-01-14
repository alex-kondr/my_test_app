from agent import *
from models.products import *
import simplejson, re


XCATS = ['Kabler', 'Velkommen til Vinyl', 'Sådan bruger du pladespilleren']


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


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.hifiklubben.dk'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@class="navigation-menu__section"]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCATS:
            sub_cats = cat.xpath('ul[@aria-hidden="true"]/li/a')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string()

                if ' alt ' not in sub_name and ' alle ' not in sub_name and sub_name not in XCATS:
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name, prods_url=url))


def process_prodlist(data, context, session):
    prods = data.xpath('//a[@class="product-card__brand-name"]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    prods_cnt = context.get('prods_cnt', data.xpath('//div[@class="filter-result-count"]/text()').string().replace('produkter', ''))
    offset = context.get('offset', 0) + 39
    next_page = context.get('page', 0) + 1
    if prods_cnt and offset < int(prods_cnt):
        session.queue(Request(context['prods_url'] + '?page=' + str(next_page)), process_prodlist, dict(context, prods_cnt=prods_cnt, offset=offset, page=next_page))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-3]
    product.category = context['cat']

    prod_json = data.xpath('//script[contains(., "Product")]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')

        mpn = prod_json.get('productID')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('gtin14')
        if ean and ean.isdigit() and len(ean) > 12:
            product.add_property(type='id.ean', value=ean)

    context['product'] = product

    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs_json = data.xpath('//script[contains(., "entries")]/text()').string()
    if revs_json:
        revs_json = simplejson.loads(revs_json.replace('\\\\\\"', "'").replace('\\\\"', "'").replace('\\"', '"').split('"entries":')[-1].split(']}', 1)[0] + ']')

        for rev in revs_json:
            is_translated = rev.get('translatedText')
            if is_translated:
                continue

            review = Review()
            review.type = 'user'
            review.ssid = product.ssid
            review.url = product.url

            date = rev.get('date')
            if date:
                review.date = date.split('T')[0]

            author = rev.get('name')
            if author:
                review.authors.append(Person(name=author, ssid=author))

            grade_overall = rev.get('rating')
            if grade_overall:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

            is_verified = rev.get('verified')
            if is_verified:
                review.add_property(type='is_verified_buyer', value=True)

            excerpt = rev.get('text')
            if excerpt:
                excerpt = remove_emoji(excerpt).strip()
                if len(excerpt) > 2:
                    review.add_property(type='excerpt', value=excerpt)

                    product.reviews.append(review)

    if product.reviews:
        session.emit(product)
