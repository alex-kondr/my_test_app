from agent import *
from models.products import *
import simplejson
import re
import time
import random


XCAT = ['All Products', 'Angebote unter 20 €', 'B-Ware', 'Black Friday', 'Black Weeks', 'Black Weeks2', 'Cyber Monday', 'Gesamtes Filterzubehor', 'Summer Black Friday']


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


def serialize_text(text):
    text = re.sub(r'&([a-zA-Z]+);', lambda match: '&' + match.group(1).lower() + ';', text).replace('<br />', ' ').replace('<br/>', ' ').replace('<br/', ' ').replace("\r", "").replace("\n", "").replace('\t', '').replace('&', '&').replace('°', '°').replace('œ', 'œ').replace('í', 'í').replace('ú', 'ú').replace('“', '"').replace('£', '£').replace('"', '"').replace('à', 'à').replace('é', 'é').replace('á', 'á').replace('´', '́').replace('ã', 'ã').replace('ç', 'ç').replace('ó', 'ó').replace('€', '€').replace('ê', 'ê').replace('è', 'è').replace('’', '’').replace('”', '”').replace(' ', ' ').replace('<', '<').replace('>', '>').replace('‘', '‘').replace('–', '–').replace('ä', 'ä').replace('ß', 'ß').replace('ö', 'ö').replace('ü', 'ü').replace('â', 'â').replace('õ', 'õ').replace('ø', 'ø').replace('…', '…').replace('„', '„').replace('—', '—').strip(' ,\n+-*~^_')
    return text


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
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.rollei.de/collections/', use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    cats = data.xpath('//div[contains(@class, "list-collection")]//div[contains(@class, "card")]/a')
    for cat in cats:
        name = cat.xpath('div[contains(@class, "content")]//span[contains(@class, "text")]/text()[normalize-space()]').string()
        url = cat.xpath('@href').string()
        if url and name not in XCAT and 'Mach ' not in name and 'top producte' not in name.lower():
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name))

    next_url = data.xpath('//div[contains(@class, "pagination")]/a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_catlist, dict())


def process_prodlist(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    prods = data.xpath('//div[contains(@id, "Product")]//motion-list/div[contains(@class, "product-card")]')
    for prod in prods:
        name = prod.xpath('.//a[contains(@class, "title")]/text()[normalize-space()]').string()
        url = prod.xpath('.//a[contains(@class, "title")]/@href').string()

        revs_cnt = prod.xpath('.//div[contains(@class, "rating")]/@title').string()
        if revs_cnt:
            revs_cnt = revs_cnt.split()[0]
            if revs_cnt.isdigit() and int(revs_cnt) > 0:
                url = 'https://www.rollei.de/products/' + url.split('/products/')[-1]
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    #   Loaded all prods


def process_product(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//product-info/@data-product-id').string()
    product.sku = data.xpath('//span[@data-current-sku]/text()[normalize-space()]').string()
    product.category = context['cat']
    product.manufacturer = 'Rollei'

    ean = data.xpath('//span[@data-current-barcode]/text()[normalize-space()]').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs_url = "https://cdn.fera.ai/api/v3/public/products/{}/reviews.json?client=fjs-3.3.6&api_key=pk_7f2fd279edefe8b4c08623df6c92c01b6dfa1996ea6fac42a2b22945361b8faa&page_size=6&sort_by=quality%3Adesc&include_aggregate_rating=true&offset=0&limit=6&include_product=true".format(product.ssid)
    session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('data', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('id')

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('customer')
        if author:
            author_name = remove_emoji(serialize_text(author.get('display_name', '')))
            author_ssid = author.get('id')
            if author_name and author_ssid:
                review.authors.append(Person(name=author_name, ssid=author_ssid))
            elif author_name:
                review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = rev.get('rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('is_verified')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('heading')
        excerpt = rev.get('body')
        if excerpt and len(remove_emoji(serialize_text(excerpt))) > 2:
            if title:
                review.title = remove_emoji(serialize_text(title))
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(serialize_text(excerpt))
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 6
    revs_cnt = context.get('revs_cnt', revs_json.get('meta', {}).get('total_count', 0))
    if offset < revs_cnt:
        next_url = 'https://cdn.fera.ai/api/v3/public/products/{ssid}/reviews.json?client=fjs-3.3.6&api_key=pk_7f2fd279edefe8b4c08623df6c92c01b6dfa1996ea6fac42a2b22945361b8faa&page_size=6&sort_by=quality%3Adesc&include_aggregate_rating=true&offset={offset}&limit=6&include_product=true'.format(ssid=product.ssid, offset=offset)
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, offset=offset, revs_cnt=revs_cnt))

    elif product.reviews:
        session.emit(product)
