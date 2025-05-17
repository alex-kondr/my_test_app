from agent import *
from models.products import *
import simplejson
import HTMLParser
import re


h = HTMLParser.HTMLParser()
XCAT = ['Alla produkter']
PROD_ID = []


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
    session.queue(Request('https://www.nutrilett.se/c/alla-produkter', use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//a[contains(@class, "transition-all")]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="" and div/h6]/div/a')
    for prod in prods:
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, url=url))

    next_url = data.xpath('//a[contains(., "Visa mer")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = data.xpath('//h1[contains(@class, "font-normal")]/text()').string()
    product.url = context['url']
    product.category = context['cat']

    prod_json = data.xpath('//script[@type="application/json"]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json).get('props', {}).get('pageProps', {}).get('lipscoreProduct', {})

        product.ssid = str(prod_json.get('id'))
        product.sku = product.ssid
        product.manufacturer = prod_json.get('brand')

        ean = prod_json.get('gtin')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

        revs_cnt = prod_json.get('review_count', 0)
        if revs_cnt and int(revs_cnt) > 0 and product.ssid not in PROD_ID:
            PROD_ID.append(product.ssid)
            revs_url = 'https://www.nutrilett.se/api/reviews?productId={}&page=1&perPage=4'.format(product.ssid)
            session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, revs_cnt=revs_cnt))


def process_reviews(data, context, session):
    product = context['product']

    revs = simplejson.loads(data.content)
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

        grade_overall = rev.get('rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.get('votes_up')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('votes_down')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        excerpt = rev.get('text')
        if excerpt:
            excerpt = remove_emoji(h.unescape(excerpt)).replace('\n', ' ').strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 4
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.nutrilett.se/api/reviews?productId={ssid}&page={page}&perPage=4'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
