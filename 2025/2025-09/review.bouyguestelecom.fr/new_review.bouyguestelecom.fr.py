from agent import *
from models.products import *
import simplejson
import HTMLParser
import re


h = HTMLParser.HTMLParser()


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
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request('https://www.bouyguestelecom.fr/telephones-mobiles?sort=meilleures-ventes', force_charset='utf-8', use='curl', max_age=0), process_prodlist, dict(cat='Smartphone'))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "fullhd")]')
    for prod in prods:
        name = prod.xpath('.//div/a[contains(@class, "product-card-title")]/text()').string()
        url = prod.xpath('.//div/a[contains(@class, "product-card-title")]/@href').string()
        ssid = prod.xpath('.//div/a[contains(@class, "product-card-title")]/@data-gencode').string()

        revs_cnt = prod.xpath('.//div/p[contains(@class, "rating-text")]/text()').string(multiple=True)
        if revs_cnt and int(revs_cnt.split()[0].strip(' (')) > 0:
            session.queue(Request(url, force_charset='utf-8', use='curl', max_age=0), process_product, dict(context, name=name, url=url, ssid=ssid))

    next_url = data.xpath('//a[@class="pagination-next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8', use='curl', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = context['cat']

    prod_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')
        #product.sku = prod_json.get('sku')

        ean = prod_json.get('gtin13', '')
        if ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_url = 'https://www.bouyguestelecom.fr/webapi/reviews?gencode=%s&limit=5' % product.ssid
    session.do(Request(revs_url, force_charset='utf-8', use='curl', max_age=0), process_reviews, dict(product=product))


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
            author = h.unescape(author).strip(".*-+_;' ")
            if author:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('note')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_recommended = rev.get('isRecommended')
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        is_verified = rev.get('user', {}).get('isVerified')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.get('message')
        title = rev.get('title')
        if excerpt and len(h.unescape(remove_emoji(excerpt)).strip(".*-+_;' ")) > 2:
            if title:
                review.title = h.unescape(remove_emoji(title)).strip(".*-+_;'? ")
        else:
            excerpt = title

        if excerpt:
            excerpt = h.unescape(remove_emoji(excerpt)).strip(".*-+_;' ")
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    revs_cnt = context.get('revs_cnt', revs_json.get('reviewCount'))
    offset = context.get('offset', 0) + 5
    if revs_cnt > offset:
        next_url = 'https://www.bouyguestelecom.fr/webapi/reviews?gencode=%s&offset=%s&limit=5' % (product.ssid, offset)
        session.do(Request(next_url, force_charset='utf-8', use='curl', max_age=0), process_reviews, dict(product=product, revs_cnt=revs_cnt, offset=offset))

    elif product.reviews:
        session.emit(product)