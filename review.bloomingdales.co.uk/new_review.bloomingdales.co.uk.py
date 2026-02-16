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
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.bloomingdales.com/shop/mens/watches?id=1000066', use='curl', options=OPTIONS, max_age=0, force_charset='utf-8'), process_prodlist, dict(cat='Watches|Male'))
    session.queue(Request('https://www.bloomingdales.com/shop/jewelry-accessories/womens-watches?id=1230061', use='curl', options=OPTIONS, max_age=0, force_charset='utf-8'), process_prodlist, dict(cat='Watches|Female'))


def process_prodlist(data, context, session):
    prods = data.xpath('//li[@class="cell sortablegrid-product"]//div[contains(@class, "product-description")]')
    for prod in prods:
        url = prod.xpath('.//a/@href').string()
        name = prod.xpath('.//h3[contains(@class, "product-name")]/text()').string()
        brand = prod.xpath('.//div[contains(@class, "product-brand")]/text()').string()

        revs_count = prod.xpath('.//span[@class="rating-description"]/span/text()').string()
        if revs_count and int(revs_count.replace(',', '')) > 0:
            session.queue(Request(url, use='curl', options=OPTIONS, max_age=0, force_charset='utf-8'), process_product, dict(context, url=url, name=name, brand=brand))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', options=OPTIONS, max_age=0, force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url'].split("&")[0]
    product.ssid = get_url_parameter(product.url, 'ID')
    product.category = context['cat']
    product.manufacturer = context['brand']

    ean = data.xpath('''//script[contains(text(), '"upcNumber"')]//text()''').string()
    if ean:
        ean = ean.split('upcNumber":"')[-1].split('"')[0]
        if ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_url = 'https://www.bloomingdales.com/xapi/digital/v1/product/' + product.ssid + '/reviews?offset=0'
    session.do(Request(revs_url, use='curl', options=OPTIONS, max_age=0, force_charset='utf-8'), process_reviews, dict(context, product=product))


def process_reviews(data, context, session):
    product = context['product']

    try:
        revs_json = simplejson.loads(data.content).get('productReviews', [])
        if not revs_json:
            return
    except:
        return

    revs_json = revs_json[0].get('paginatedReviews', {})

    revs = revs_json.get('reviews', [])
    for rev in revs:
        is_syndicated = rev.get('syndicated')
        if is_syndicated:
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev['reviewId'])
        review.date = rev.get('submissionTime')

        author = rev.get('userNickname', rev.get('displayName'))
        author_id = rev.get('authorId')
        if author and author_id:
            review.authors.append(Person(name=author, ssid=author_id))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.get('totalPositiveFeedbackCount')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('totalNegativeFeedbackCount')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        is_recommended = rev.get('recommended')
        if is_recommended:
            review.add_property(value=True, type='is_recommended')

        title = rev.get('title')
        excerpt = rev.get('reviewText')
        if excerpt and len(remove_emoji(excerpt).strip()) > 2:
            if title:
                review.title = remove_emoji(title)
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = revs_json.get('total', 0)
    offset = context.get('offset', 0) + 30
    if offset < revs_cnt:
        next_url = 'https://www.bloomingdales.com/xapi/digital/v1/product/' + product.ssid + '/reviews?offset=' + str(offset)
        session.do(Request(next_url, use='curl', options=OPTIONS, max_age=0, force_charset='utf-8'), process_reviews, dict(product=product, offset=offset))

    elif product.reviews:
        session.emit(product)
