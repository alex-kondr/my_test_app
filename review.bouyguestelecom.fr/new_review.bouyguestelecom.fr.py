from agent import *
from models.products import *
import simplejson
import re


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
    session.queue(Request('https://www.bouyguestelecom.fr/telephones-mobiles/', use='curl', max_age=0), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "has-text-centered product-card")]')
    for prod in prods:
        name = prod.xpath('.//p[contains(@class, "product-card-title")]/text()').string()
        url = prod.xpath('a/@href').string()

        revs_cnt = prod.xpath('.//p[contains(@class, "rating-text")]/text()')
        if revs_cnt:
            session.queue(Request(url, use='curl', max_age=0), process_product, dict(name=name, url=url))

    next_url = data.xpath('//a[@class="pagination-next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', max_age=0), process_prodlist, dict())


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = 'Smartphone'

    prod_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')

        mpn = prod_json.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('gtin13')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    gencode = data.xpath('//script[contains(., "gencode")]/text()').string()
    if gencode:
        gencode = gencode.replace('\\"', '"').split(',"gencode":"', 1)[-1].split('","urlKey":"')[0]
        revs_url = 'https://www.bouyguestelecom.fr/webapi/reviews?gencode={}&limit=5'.format(gencode)
        session.do(Request(revs_url), process_reviews, dict(product=product, gencode=gencode))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('reviews')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('user', {}).get('login')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('note')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('user', {}).get('isVerified')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        is_recommended = rev.get('isRecommended')
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        title = rev.get('title')
        excerpt = rev.get('message')
        if excerpt and len(remove_emoji(excerpt).strip(' +-*.')) > 1 and title:
            review.title = remove_emoji(title).strip(' +-*.')
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip(' +-*.')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    revs_cnt = revs_json.get('reviewCount')
    offset = context.get('offset', 5) + 5
    if offset < revs_cnt:
        next_url = 'https://www.bouyguestelecom.fr/webapi/reviews?gencode={gencode}&offset={offset}&limit=5'.format(gencode=context['gencode'], offset=offset)
        session.do(Request(next_url), process_reviews, dict(context, product=product, offset=offset))

    elif product.reviews:
        session.emit(product)
