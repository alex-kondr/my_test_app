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
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request('https://www.bouyguestelecom.fr/webapi/wall?type=phone&options={"sort":"meilleures-ventes","page":1,"limit":28,"filters":{},"plan":"7017","stickers":["0","1","6","7","8","9","14","15"]}&shouldBeProspect=false', force_charset='utf-8', max_age=0), process_prodlist, dict())


def process_prodlist(data, context, session):
    try:
        prods_json = simplejson.loads(data.content)
    except:
        prods_json = {}

    prods = prods_json.get('products', [])
    for prod in prods:
        product = Product()
        product.url = 'https://www.bouyguestelecom.fr' + prod.get('url')
        product.ssid = prod.get('gencode')
        product.category = 'Smartphone'
        product.manufacturer = prod.get('brand')

        revs_cnt = prod.get('rating', {}).get('count')
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(product.url, force_charset='utf-8', max_age=0), process_product, dict(product=product, revs_cnt=int(revs_cnt)))

    prods_cnt = context.get('prods_cnt', prods_json.get('count'))
    offset = context.get('offset', 0) + len(prods)
    if offset < prods_cnt:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.bouyguestelecom.fr/webapi/wall?type=phone&options={"sort":"meilleures-ventes","page":' + str(next_page) + ',"limit":28,"filters":{},"plan":"7017","stickers":["0","1","6","7","8","9","14","15"]}&shouldBeProspect=false'
        session.queue(Request(next_url, force_charset='utf-8', max_age=0), process_prodlist, dict(prods_cnt=prods_cnt, offset=offset, page=next_page))


def process_product(data, context, session):
    product = context['product']

    product.name = data.xpath('//div[@class="product-title"]//h1[contains(@class, "title")]/text()').string()

    prod_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        mpn = prod_json.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('gtin13')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_url = 'https://www.bouyguestelecom.fr/webapi/reviews?gencode=%s&limit=5' % product.ssid
    session.do(Request(revs_url, force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product))


def process_reviews(data, context, session):
    product = context['product']

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('reviews', [])
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
            if author and 'anonymous' != author:
                review.authors.append(Person(name=author, ssid=author))
            else:
                author = None

        grade_overall = rev.get('note')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_recommended = rev.get('isRecommended')
        if is_recommended is True:
            review.add_property(type='is_recommended', value=True)

        is_verified = rev.get('user', {}).get('isVerified')
        if is_verified is True:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('title')
        excerpt = rev.get('message')
        if excerpt and len(h.unescape(remove_emoji(excerpt)).strip(".*-+_;' ")) > 2:
            if title and title != excerpt:
                review.title = h.unescape(remove_emoji(title)).strip(".*-+_;'? ")
        else:
            excerpt = title

        if excerpt:
            excerpt = h.unescape(remove_emoji(excerpt)).strip(".*-+_;' ")
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        next_url = 'https://www.bouyguestelecom.fr/webapi/reviews?gencode=%s&offset=%s&limit=5' % (product.ssid, offset)
        session.do(Request(next_url, force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, offset=offset))

    elif product.reviews:
        session.emit(product)