from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Brands']
MPNS = []


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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.storedj.com.au/', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats_json = data.xpath('//script[contains(., "remixContext = {")]/text()').string()
    if not cats_json:
        return

    cats = simplejson.loads(cats_json.split('remixContext =')[-1].split(';__remixContext.p')[0].strip()).get('state', {}).get('loaderData', {}).get('root', {}).get('categoryData', [])
    for cat in cats:
        name = cat.get('categoryName')

        if name and name not in XCAT:
            sub_cats = cat.get('subCats', [])
            for sub_cat in sub_cats:
                sub_name = sub_cat.get('categoryName')

                if sub_name:
                    options = """--compressed -X POST --data-raw '{"searches":[{"query_by":"title,description,sid","highlight_full_fields":"title,sid","query_by_weights":"10,1,1","num_typos":1,"typo_tokens_threshold":1,"sort_by":"_text_match:desc,globalSortOverride:desc,globalSortOrder:desc","enable_overrides":true,"per_page":20,"collection":"sdj_products","q":"*","facet_by":"brand,catdesc.lvl0,catdesc.lvl1,catdesc.lvl2,in_stock,price,product_status","filter_by":"catdesc.lvl1:=[`""" + name + ' > ' + sub_name + """]","max_facet_values":200,"page":1}]}'"""
                    url = 'https://search.soundbay.com.au/multi_search?x-typesense-api-key=465FSQRbitoh2YfhEMZAMwjdMlbmLYhc'
                    session.do(Request(url, use='curl', options=options, force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name + '|' + sub_name, cat_name=name, sub_catname=sub_name))


def process_prodlist(data, context, session):
    prods_json = simplejson.loads(data.content)
    if not prods_json:
        return

    prods_json = prods_json.get('results', [])[0]

    prods = prods_json.get('hits', [])
    for prod in prods:
        prod = prod.get('document')

        product = Product()
        product.name = prod.get('title')
        product.url = 'https://www.storedj.com.au/products/' + prod.get('url')
        product.ssid = prod.get('sid')
        product.sku = product.ssid
        product.category = context['cat']
        product.manufacturer = prod.get('Brand')

        mpn = prod.get('parent_product') or prod.get('id')
        if not mpn or mpn in MPNS:
            continue

        MPNS.append(mpn)
        product.add_property(type='id.manufacturer', value=mpn)

        ean = prod.get('shopifyId')
        if ean:
            product.add_property(type='id.ean', value=str(ean))

        revs_url = 'https://api.trustpilot.com/v1/product-reviews/business-units/5487e55500006400057c0ed1/reviews?apikey=7qfADKhmajegupAzebRovRVAjxdpou0s&sku={}&perPage=100'.format(mpn)
        session.do(Request(revs_url, force_charset='utf-8', max_age=0), process_reviews, dict(product=product))

    prods_cnt = prods_json.get('found')
    offset = context.get('offset', 0) + 20
    next_page = context.get('page', 1) + 1
    if offset < prods_cnt:
        options = """--compressed -X POST --data-raw '{"searches":[{"query_by":"title,description,sid","highlight_full_fields":"title,sid","query_by_weights":"10,1,1","num_typos":1,"typo_tokens_threshold":1,"sort_by":"_text_match:desc,globalSortOverride:desc,globalSortOrder:desc","enable_overrides":true,"per_page":20,"collection":"sdj_products","q":"*","facet_by":"brand,catdesc.lvl0,catdesc.lvl1,catdesc.lvl2,in_stock,price,product_status","filter_by":"catdesc.lvl1:=[`""" + context['cat_name'] + ' > ' + context['sub_catname'] + """]","max_facet_values":200,"page":""" + str(next_page) + """}]}'"""
        next_url = 'https://search.soundbay.com.au/multi_search?x-typesense-api-key=465FSQRbitoh2YfhEMZAMwjdMlbmLYhc'
        session.do(Request(next_url, use='curl', options=options, force_charset='utf-8', max_age=0), process_prodlist, dict(context, page=next_page, offset=offset))


def process_reviews(data, context, session):
    product = context['product']

    revs = simplejson.loads(data.content).get('productReviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('id')

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('consumer', {}).get('displayName', '').strip(' +-')
        author_ssid = rev.get('consumer', {}).get('id')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=author_ssid))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('stars')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('content')
        if excerpt:
            excerpt = remove_emoji(excerpt).strip(' +-()')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)
