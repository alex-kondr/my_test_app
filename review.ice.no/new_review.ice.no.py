from agent import *
from models.products import *
import simplejson
import re


API = '14d81fbe538344317cfc0199'
OPTIONS = """-H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0' -H 'Accept: application/json, text/javascript, */*; q=0.01' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Origin: https://nettbutikk.ice.no' -H 'Connection: keep-alive' -H 'Referer: https://nettbutikk.ice.no/' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: cross-site' -H 'Priority: u=0' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""


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
    session.queue(Request('https://nettbutikk.ice.no/mobiltelefoner', use='curl'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//a[contains(@class, "items-center") and span]')
    for cat in cats:
        name = cat.xpath('span[@data-text]/text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//a[@data-testid="product-card"]')
    for prod in prods:
        name = prod.xpath('@title').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

# no next page


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//button/@data-ls-product-id').string()
    product.category = context['cat']
    product.namufacturer = data.xpath('//button/@data-ls-brand').string()

    ean = data.xpath('//button/@data-ls-gtin').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    prod_json = data.xpath('//script[@type="application/json"]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json).get('props', {}).get('pageProps', {}).get('variant', {}).get('specifications', [])
        for info in prod_json:
            if info.get('name') == 'Fabrikantmodellnummer':
                product.add_property(type='id.manufacturer', value=info.get('value'))
                break

    revs_url = 'https://wapi.lipscore.com/initial_data/products/show?api_key={api}&internal_id={id}&widgets=rw_l%2Crw_smr&translate_to_lang=no'.format(id=product.ssid, api=API)
    session.do(Request(revs_url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    if context.get('page'):
        revs = revs_json
    else:
        context['prod_id'] = revs_json.get('id')
        context['revs_cnt'] = revs_json.get('review_count')

        revs = revs_json.get('reviews', [])

    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('user', {}).get('name')
        author_ssid = rev.get('user', {}).get('id')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=str(author_ssid)))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('lipscore')
        if grade_overall:
            grade_overall = grade_overall / 2
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        is_verified = rev.get('purchase_date')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('votes_up')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=hlp_yes)

        hlp_no = rev.get('votes_down')
        if hlp_no:
            review.add_property(type='helpful_votes', value=hlp_no)

        excerpt = rev.get('text')
        if excerpt:
            excerpt = remove_emoji(excerpt).strip(' +-.*')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        next_url = 'https://wapi.lipscore.com/products/{prod_id}/reviews?api_key={api}&page={next_page}&translate_to_lang=no'.format(prod_id=context['prod_id'], next_page=next_page, api=API)
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0, options=OPTIONS), process_reviews, dict(context, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
