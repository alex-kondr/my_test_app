from agent import *
from models.products import *
import simplejson
import re


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3'"""


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
    session.queue(Request('https://www.bloomingdales.com/shop/mens/watches/Productsperpage/120?id=1000066', use='curl', options=OPTIONS, max_age=0, force_charset='utf-8'), process_prodlist, dict(cat='Watches|Male'))
    session.queue(Request('https://www.bloomingdales.com/shop/jewelry-accessories/watches/Productsperpage/120?id=19469', use='curl', options=OPTIONS, max_age=0, force_charset='utf-8'), process_prodlist, dict(cat='Watches|Female'))


def process_prodlist(data, context, session):
    prods = data.xpath('//ul[contains(@class, "items")]/li')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('.//div[@class="product-name"]/text()').string()
        product.manufacturer = prod.xpath('.//div[@class="product-brand heavy"]/text()').string()
        product.url = prod.xpath('.//a[@class="brand-and-name"]/@href').string()
        product.category = context['cat']

        ssid = prod.xpath('@data-product-id').string()
        if not ssid:
            ssid = prod.xpath('.//div/@id').string()

        product.ssid = ssid.split('-')[-1]
        product.sku = product.ssid

        revs_cnt = prod.xpath('.//span[@class="rating-description"]//text()').string(multiple=True)
        if revs_cnt:
            revs_url = 'https://www.bloomingdales.com/xapi/digital/v1/product/{}/reviews'.format(product.ssid)
            session.queue(Request(revs_url, use='curl', options=OPTIONS, force_charset="utf-8", max_age=0), process_reviews, dict(product=product))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.do(Request(next_url, use='curl', options=OPTIONS, force_charset="utf-8", max_age=0), process_prodlist, dict(context))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('review', {}).get('reviews', [])
    for rev in revs:
        if rev.get('syndicated'):
            # The review is from another site or another product
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev['reviewId'])
        review.date = rev.get('submissionTime')

        title = rev.get('title')
        if title:
            review.title = remove_emoji(title).strip()

        author_name = rev.get('displayName')
        author_ssid = rev.get('buyerId')
        if author_name and author_ssid:
            review.authors.append(Person(name=author_name, ssid=str(author_ssid)))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        badges = rev.get('badgesOrder', [])
        if "verifiedPurchaser" in badges:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('totalPositiveFeedbackCount')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('totalNegativeFeedbackCount')
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        is_recommended = rev.get('recommended')
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('reviewText')
        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', ' ').replace('\r', '').strip()
            if excerpt:
                review.add_property(type='excerpt', value=excerpt)
                product.reviews.append(review)

    revs_cnt = context.get('revs_cnt', revs_json.get('review', {}).get('totalResults', 0))
    offset = 8 if not context.get('offset') else context['offset'] + 30
    if revs_cnt > offset:
        revs_url = 'https://www.bloomingdales.com/xapi/digital/v1/product/{pid}/reviews?offset={offset}'.format(pid=product.ssid, offset=offset)
        session.do(Request(revs_url, use='curl', options=OPTIONS, force_charset="utf-8", max_age=0), process_reviews, dict(revs_cnt=revs_cnt, product=product, offset=offset))
    elif product.reviews:
        session.emit(product)
