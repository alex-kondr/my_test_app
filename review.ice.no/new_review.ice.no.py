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



def run(context, session):
    session.queue(Request('https://nettbutikk.ice.no/mobiltelefoner', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//ul[@data-analytics-id="tabs"]/li/a')
    for cat in cats:
        name = cat.xpath('@title').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@data-testid="products-grid"]/a')
    for prod in prods:
        name = prod.xpath('@data-analytics-product-name').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url))

    # No next page


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//button/@data-ls-product-id').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//button/@data-ls-brand').string()

    ean = data.xpath('//button/@data-ls-gtin').string()
    if ean and len(ean) > 10 and ean.isdigit():
        product.add_property(type='id.ean', value=ean)

    revs_url = 'https://wapi.lipscore.com/initial_data/products/show?api_key={api_key}&internal_id={ssid}&widgets=rw_l%2Crw_smr'.format(api_key=API_KEY, ssid=product.ssid)
    session.do(Request(revs_url, use='curl', options=OPTIONS, force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
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

        author = rev.get('user', {})
        if author:
            author_name = h.unescape(remove_emoji(author.get('name') or author.get('short_name'))).strip()
            author_ssid = str(author.get('id'))
            review.authors.append(Person(name=author_name, ssid=author_ssid))

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        hlp_yes = rev.get('votes_up')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=hlp_yes)

        hlp_no = rev.get('votes_down')
        if hlp_no:
            review.add_property(type='helpful_votes', value=hlp_no)

        is_verified = rev.get('purchase_date')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        grade_overall = rev.get('lipscore')
        if grade_overall:
            grade_overall = grade_overall / 2.0
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        excerpt = rev.get('text')
        if excerpt:
            excerpt = h.unescape(remove_emoji(excerpt)).strip(' .+')
            if excerpt:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        next_url = 'https://wapi.lipscore.com/products/{0}/reviews?api_key={1}&page={2}'.format(context['prod_id'], API_KEY, next_page)
        session.do(Request(next_url, use='curl', options=OPTIONS, force_charset='utf-8', max_age=0), process_reviews, dict(context, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
