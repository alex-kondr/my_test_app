from agent import *
from models.products import *
import simplejson
import re


CAT = ['Fragrance', 'Sun & Tan', 'Haircare', 'Skincare', 'Makeup', 'Bath & Body', 'Nails', 'Electricals', 'Home & Candles', 'Health & Wellbeing']
XCAT = ['Shop All', 'Gift Sets for her', 'Gift sets for him', 'BEST-SELLERS', 'Best-Sellers']


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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.justmylook.com/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//nav[@class="h-full"]/ul/ul/div')
    for cat in cats:
        name = cat.xpath('div/h2/text()').string()
        url = cat.xpath('div/div/a/@href').string()

        if name in CAT:
            session.queue(Request(url), process_category, dict(cat=name))


def process_category(data, context, session):
    strip_namespace(data)

    subcats = data.xpath('//a[contains(@class, "group/collection-link")]')
    for subcat in subcats:
        subcat_name = subcat.xpath('.//p/text()').string()
        cat_id = subcat.xpath('@href').string().split('/')[-1]

        if subcat_name not in XCAT:
            options = """--compressed -X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0' -H 'Accept: */*' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'content-type: application/x-www-form-urlencoded' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: cross-site' -H 'Priority: u=0' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' --data-raw '{"requests":[{"indexName":"shopify_products","params":"clickAnalytics=true&distinct=true&facetingAfterDistinct=true&facets=%5B%22meta.algolia.colour_description%22%2C%22meta.algolia.fragrance_classification%22%2C%22meta.algolia.fragrance_notes%22%2C%22meta.algolia.fragrance_type%22%2C%22meta.algolia.gender%22%2C%22meta.algolia.hair_type_concern%22%2C%22meta.algolia.healthcare_concern%22%2C%22meta.algolia.home_fragrance_scent%22%2C%22meta.algolia.key_ingredient%22%2C%22meta.algolia.nail_polish_colour%22%2C%22meta.algolia.product_type%22%2C%22meta.algolia.skin_concern%22%2C%22meta.algolia.skin_type%22%2C%22meta.algolia.spf_content%22%2C%22meta.algolia.supplement_format%22%2C%22meta.algolia.supplement_type%22%2C%22price%22%2C%22price_range%22%2C%22product_type%22%2C%22vendor%22%5D&filters=collections%3A""" + cat_id + """&highlightPostTag=__%2Fais-highlight__&highlightPreTag=__ais-highlight__&hitsPerPage=24&maxValuesPerFacet=200&page=1&query=&ruleContexts=%5B%22""" + cat_id + """%22%2C%22shopify_default_collection%22%5D&userToken=anonymous-d8522922-34ba-46a4-9cab-02fe1f574c28"}]}'"""
            url = 'https://b9ln8d81oh-dsn.algolia.net/1/indexes/*/queries?x-algolia-agent=Algolia%20for%20JavaScript%20(4.20.0)%3B%20Browser%20(lite)%3B%20instantsearch.js%20(4.80.0)%3B%20Shopify%20Integration%3B%20Shopify%20App%20Blocks%3B%20JS%20Helper%20(3.26.0)&x-algolia-api-key=4cfe086f749400902a5c1af3a90a2096&x-algolia-application-id=B9LN8D81OH'
            session.do(Request(url, use='curl', options=options, max_age=0), process_prodlist, dict(cat=context['cat']+'|'+subcat_name, cat_id=cat_id))


def process_prodlist(data, context, session):
    strip_namespace(data)

    try:
        prods_json = simplejson.loads(data.content).get('results')[0]
    except:
        prods_json = {}

    prods = prods_json.get('hits', [])
    for prod in prods:
        product = Product()
        product.name = prod.get('title')
        product.url = 'https://www.justmylook.com/products/' + prod.get('handle')
        product.ssid = str(prod.get('id'))
        product.sku = str(prod.get('sku'))
        product.category = context['cat'].title()
        product.manufacturer = prod.get('vendor')

        ean = prod.get('barcode')
        if ean and str(ean).isdigit() and len(str(ean)) > 10:
            product.add_property(type='id.ean', value=str(ean))

        revs_cnt = prod.get('meta', {}).get('reviewscouk', {}).get('total', 0)
        if revs_cnt and int(revs_cnt) > 0:
            data_sku = product.sku + ';' + prod.get('objectID') + ';' + product.ssid + ';' + prod.get('handle')
            url = 'https://api.reviews.io/timeline/data?type=product_review&store=just-my-look1&sort=date_desc&page={}&per_page=7&include_sentiment_analysis=true&widget=polaris&sku=' + data_sku + '&lang=en&enable_avatars=true&include_subrating_breakdown=1'
            session.do(Request(url.format(1), max_age=0), process_reviews, dict(product=product, revs_cnt=int(revs_cnt), revs_url=url))

    prods_cnt = context.get('prods.cnt', prods_json.get('nbHits', 0))
    offset = context.get('offset', 0) + 24
    if offset < prods_cnt:
        next_page = context.get('page', 1) + 1
        options = """--compressed -X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0' -H 'Accept: */*' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'content-type: application/x-www-form-urlencoded' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: cross-site' -H 'Priority: u=0' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' --data-raw '{"requests":[{"indexName":"shopify_products","params":"clickAnalytics=true&distinct=true&facetingAfterDistinct=true&facets=%5B%22meta.algolia.colour_description%22%2C%22meta.algolia.fragrance_classification%22%2C%22meta.algolia.fragrance_notes%22%2C%22meta.algolia.fragrance_type%22%2C%22meta.algolia.gender%22%2C%22meta.algolia.hair_type_concern%22%2C%22meta.algolia.healthcare_concern%22%2C%22meta.algolia.home_fragrance_scent%22%2C%22meta.algolia.key_ingredient%22%2C%22meta.algolia.nail_polish_colour%22%2C%22meta.algolia.product_type%22%2C%22meta.algolia.skin_concern%22%2C%22meta.algolia.skin_type%22%2C%22meta.algolia.spf_content%22%2C%22meta.algolia.supplement_format%22%2C%22meta.algolia.supplement_type%22%2C%22price%22%2C%22price_range%22%2C%22product_type%22%2C%22vendor%22%5D&filters=collections%3A""" + context['cat_id'] + """&highlightPostTag=__%2Fais-highlight__&highlightPreTag=__ais-highlight__&hitsPerPage=24&maxValuesPerFacet=200&page=""" + str(next_page) + """&query=&ruleContexts=%5B%22""" + context['cat_id'] + """%22%2C%22shopify_default_collection%22%5D&userToken=anonymous-d8522922-34ba-46a4-9cab-02fe1f574c28"}]}'"""
        next_url = 'https://b9ln8d81oh-dsn.algolia.net/1/indexes/*/queries?x-algolia-agent=Algolia%20for%20JavaScript%20(4.20.0)%3B%20Browser%20(lite)%3B%20instantsearch.js%20(4.80.0)%3B%20Shopify%20Integration%3B%20Shopify%20App%20Blocks%3B%20JS%20Helper%20(3.26.0)&x-algolia-api-key=4cfe086f749400902a5c1af3a90a2096&x-algolia-application-id=B9LN8D81OH'
        session.do(Request(next_url, use='curl', options=options, max_age=0), process_prodlist, dict(context, prods_cnt=prods_cnt, offset=offset, page=next_page))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context["product"]

    try:
        revs = simplejson.loads(data.content).get('timeline', [])
    except:
        revs = []

    for rev in revs:
        rev = rev.get('_source', {})

        if product.sku != rev.get('sku'):
            continue

        review = Review()
        review.type = "user"
        review.url = product.url

        date = rev.get('date_created')
        if date:
            review.date = date.split()[0]

        author = rev.get('author')
        if author:
            author = remove_emoji(author).strip()
            if len(author) > 2 and author.lower() != 'anonymous':
                author_ssid = rev.get('user_id')
                if author_ssid:
                    review.authors.append(Person(name=author, ssid=str(author_ssid)))
                else:
                    review.authors.append(Person(name=author, ssid=author))
            else:
                author = None

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        is_verified = rev.get('order_id')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('helpful')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        is_recommended = rev.get('would_recommend_product')
        if is_recommended is True:
            review.add_property(type='is_recommended', value=True)

        excerpt = rev.get('comments')
        if excerpt:
            excerpt = remove_emoji(excerpt).replace("\r", '').replace('\n', '').strip()
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                ssid = rev.get('_id')
                if ssid:
                    review.ssid = ssid.split('-')[-1]
                else:
                    review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 7
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        session.do(Request(context['revs_url'].format(next_page), max_age=0), process_reviews, dict(context, product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
