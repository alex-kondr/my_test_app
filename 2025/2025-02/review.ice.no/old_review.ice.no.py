from agent import *
from models.products import *
import simplejson
import re


def run(context, session):
    session.queue(Request('https://nettbutikk.ice.no/mobiltelefoner', use='curl', force_charset='utf-8', max_age=0), process_category, dict())


def process_category(data, context, session):
    cats = data.xpath('//ul[@data-analytics-id="tabs"]/li/a')
    for cat in cats:
        name = cat.xpath('@title').string()
        url = cat.xpath("@href").string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//a[@data-testid="product-card"]')
    for prod in prods:
        name = prod.xpath('@title').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.manufacturer = data.xpath('//div/@data-ls-brand').string()
    product.url = context['url']
    product.category = context['cat']
    product.ssid = data.xpath('//div/@data-ls-product-id').string()

    ean = data.xpath('//div/@data-ls-gtin').string()
    if ean:
        product.properties.append(ProductProperty(type='id.ean', value=ean))

    url = 'https://wapi.lipscore.com/initial_data/products/show?api_key=14d81fbe538344317cfc0199&internal_id={}&widgets=rw_l%2Crw_smr&per_page=100'.format(product.ssid)
    session.do(Request(url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product))

    if product.reviews:
        session.emit(product)


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    revs = revs_json

    if isinstance(revs_json, dict):
        revs = revs_json.get('reviews', {})

    for rev in revs:
        lang = rev.get('lang')
        if lang != 'no':
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev['id'])

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('user', {})
        if author:
            author_name = author.get('name')
            author_ssid = author.get('id')
            if author_name and author_ssid:
                review.authors.append(Person(name=author_name, ssid=str(author_ssid)))
            elif author_name:
                review.authors.append(Person(name=author_name, ssid=author_name))

        is_verified = rev.get('purchase_date')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('votes_up')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('votes_down')
        if hlp_no:
            review.add_property(type='helpful_votes', value=int(hlp_no))

        grade_overall = rev.get('lipscore')
        if grade_overall:
            value = float(grade_overall) / 2
            review.grades.append(Grade(type="overall", value=value, best=5.0))

        excerpt = rev.get('text')
        if excerpt:
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
            excerpt = emoji_pattern.sub(r'', excerpt).replace('&nbsp;', '').strip()
            if excerpt:
                review.add_property(type='excerpt', value=excerpt)
                product.reviews.append(review)

    revs_cnt = context.get('revs_cnt') or revs_json.get('review_count')
    offset = context.get('offset', 0) + 100
    if revs_cnt and int(revs_cnt) > offset:
        next_page = context.get('page', 1) + 1
        revs_url = 'https://wapi.lipscore.com/products/{}/reviews?api_key=14d81fbe538344317cfc0199&page={}&per_page=100'.format(product.ssid, next_page)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, offset=offset, page=next_page, revs_cnt=revs_cnt))
