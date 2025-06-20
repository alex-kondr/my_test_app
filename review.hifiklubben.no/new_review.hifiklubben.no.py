from agent import *
from models.products import *
import simplejson
import re


XCATS = ['Kabler', 'Velkommen til Vinyl', 'Hvordan bruker jeg vinylspilleren?', 'Projektorlerret', 'Merker', 'Inspirasjon', 'Nyheter', 'Tilbud', 'Outlet']


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
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.hifiklubben.no', use='curl', force_charset="utf-8", max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@data-usp-bar-visible="true"]/ul/li/a')
    for cat in cats:
        name = cat.xpath('span[@data-outlet-related]/text()').string()
        if name and name not in XCATS:
            url = cat.xpath('@href').string()
            session.queue(Request(url, use='curl', force_charset="utf-8", max_age=0), process_category, dict(cat=name))


def process_category(data, context, session):
    strip_namespace(data)

    sub_cats = data.xpath('//div[@data-page-container="true"]/nav/ul/li/a')
    for sub_cat in sub_cats:
        name = sub_cat.xpath('div/text()[normalize-space(.)]').string()
        url = sub_cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset="utf-8", max_age=0), process_prodlist, dict(cat=context['cat']+'|'+name, url=url))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods_cnt = data.xpath('//div[regexp:test(normalize-space(text()), "^\\d+ produkter$")]/text()').string()
    if not prods_cnt:
        process_product(data, context, session)

    prods = data.xpath('//article[@class]/a[.//div[@data-count="true"]]')
    for prod in prods:
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset="utf-8", max_age=0), process_product, dict(context, url=url))

    prods_cnt = context.get('prods_cnt', prods_cnt)
    if prods_cnt:
        prods_cnt = prods_cnt.replace('produkter', '')

    offset = context.get('offset', 0) + 42
    next_page = context.get('page', 0) + 1
    if prods_cnt and offset < int(prods_cnt):
        next_url = context['url']+'?page='+str(next_page)
        session.queue(Request(next_url, use='curl', force_charset="utf-8", max_age=0), process_prodlist, dict(context, prods_cnt=prods_cnt, offset=offset, page=next_page))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = data.xpath('//h1//text()').string(multiple=True)
    product.url = context['url']
    product.ssid = product.url.strip('/').split('/')[-1]
    product.category = context['cat']

    prod_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')

        mpn = prod_json.get('productID')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('gtin14')
        if ean and ean.isdigit() and len(ean) > 12:
            product.add_property(type='id.ean', value=ean)

    sku = data.xpath(r'''//script[contains(., '"skuCode\"')]/text()''').string()
    if sku:
        sku = sku.split('skuCode\\":\\"', 1)[-1].split('\\')[0]

        revs_url = 'https://www.hifiklubben.no/api/v2/ratings?productId={sku}&host=www.hifiklubben.no'.format(sku=sku)
        session.do(Request(revs_url, use='curl', force_charset="utf-8", max_age=0), process_reviews, dict(context, product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    if not revs_json:
        return

    for rev in revs_json:
        market_id = rev.get('marketId')
        if market_id.upper() != 'NO':
            continue

        review = Review()
        review.type = 'user'
        review.ssid = rev.get('ratingId')
        review.url = product.url

        date = rev.get('date')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('name')
        if author and author.strip():
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.get('verified')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.get('text')
        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', ' ').strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
