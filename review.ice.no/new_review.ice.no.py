from agent import *
from models.products import *
import simplejson
import re
import HTMLParser


h = HTMLParser.HTMLParser()
API_KEY = '14d81fbe538344317cfc0199'
OPTIONS = "-H 'referer: https://nettbutikk.ice.no/'"


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


def RequestProds(page):
    options = """--compressed -X POST -H 'referer: https://nettbutikk.ice.no/' --data-raw '{"searches":[{"group_by":"productSlug","group_limit":1,"query_by":"name,manufacturer","sort_by":"isPromotedVariant:desc,defaultSortPriority:asc","highlight_full_fields":"name,manufacturer","collection":"prod_hardware_offering_variants","q":"*","facet_by":"categorySlug,isAvailableWithEquipmentUpgrade,isPentBrukt,manufacturer,regularPrice","filter_by":"isAvailable:true && isPentBrukt:=[false]","max_facet_values":20,"page":""" + str(page)+ ""","per_page":21}]}'"""
    url = 'https://y0ru34sdmgptzij9p.a2.typesense.net/multi_search?x-typesense-api-key=bS83VJco2Ufb2NShS4lrQLL5yNCCf7uz'
    r = Request(url, use='curl', force_charset='utf-8', options=options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.do(RequestProds(1), process_prodlist, dict())


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    try:
        prods_json = simplejson.loads(data.content).get('results', [{}])[0]
    except:
        prods_json = {}

    prods = prods_json.get('grouped_hits', [])
    for prod in prods:
        prod = prod.get('hits', [{}])[0].get('document', {})

        product = Product()
        product.name = prod.get('name')
        product.ssid = prod.get('lipscoreId')
        product.sku = prod.get('id')
        product.category = prod.get('categoryName')
        product.manufacturer = prod.get('manufacturer')
        product.url = 'https://nettbutikk.ice.no/' + prod.get('categorySlug') + '/' + product.manufacturer.lower() + '/' + prod.get('productSlug') + '/' + prod.get('slug')

        ean = prod.get('gtin')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

        if product.ssid:
            revs_url = 'https://wapi.lipscore.com/initial_data/products/show?api_key={api_key}&internal_id={ssid}&widgets=rw_l%2Crw_smr'.format(api_key=API_KEY, ssid=product.ssid)
            session.queue(Request(revs_url, use='curl', options=OPTIONS, force_charset='utf-8', max_age=0), process_reviews, dict(product=product))

    prods_cnt = context.get('prods_cnt', prods_json.get('found', 0))
    offset = context.get('offset', 0) + 21
    if offset < prods_cnt:
        next_page = context.get('page', 1) + 1
        session.do(RequestProds(next_page), process_prodlist, dict(prods_cnt=prods_cnt, offset=offset, page=next_page))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    if not context.get('prod_id'):
        context['prod_id'] = revs_json.get('id')
        context['revs_cnt'] = revs_json.get('review_count')
        revs = revs_json.get('reviews', [])
    else:
        revs = revs_json

    for rev in revs:
        if not rev.get('lang') or rev['lang'].lower() != 'no':
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('user', {})
        if author:
            author_name = h.unescape(remove_emoji(author.get('name') or author.get('short_name'))).strip()
            author_ssid = str(author.get('id'))
            review.authors.append(Person(name=author_name, ssid=author_ssid))

        grade_overall = rev.get('lipscore')
        if grade_overall:
            grade_overall = grade_overall / 2.0
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        hlp_yes = rev.get('votes_up')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=hlp_yes)

        hlp_no = rev.get('votes_down')
        if hlp_no:
            review.add_property(type='helpful_votes', value=hlp_no)

        is_verified = rev.get('purchase_date')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.get('text')
        if excerpt:
            excerpt = h.unescape(remove_emoji(excerpt)).replace('\n', '').replace('\r', '').strip(' .+…')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        next_url = 'https://wapi.lipscore.com/products/{prod_id}/reviews?api_key={api_key}&page={page}'.format(prod_id=context['prod_id'], api_key=API_KEY, page=next_page)
        session.do(Request(next_url, use='curl', options=OPTIONS, force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
