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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.parfym.se/', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="menu__levelc__submenu"]')
    for cat in cats:
        name = cat.xpath('.//a[@class="title"]/text()').string()

        if 'märken' not in name.lower() and 'nyheter' not in name.lower() and 'aktuella' not in name.lower() and 'populära' not in name.lower():
            sub_cats = cat.xpath('.//a[@class="pfour-menu-medium"]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string()

                if 'märken' not in sub_name:
                    session.queue(Request(url + '?layout=pfour_products', max_age=0), process_prodlist, dict(cat=name + '|' + sub_name, prods_url=url))
            else:
                url = cat.xpath('.//a[@class="title"]/@href').string()
                session.queue(Request(url + '?layout=pfour_products', max_age=0), process_prodlist, dict(cat=name, prods_url=url))


def process_prodlist(data, context, session):
    try:
        prods_json = simplejson.loads(data.content)
    except:
        return

    new_data = data.parse_fragment(prods_json.get('products'))

    prods = new_data.xpath('//div[@class="pfour-prod-item pfour-hasplusbutton"]')
    for prod in prods:
        name = prod.xpath('.//div[@class="name"]/text()').string()
        manufacturer = prod.xpath('.//div[@class="brand"]/text()').string()
        prod_id = prod.xpath('.//button/@data-productid').string()
        url = prod.xpath('.//a[@class="pfour-prod-item-link"]/@href').string()

        revs_cnt = prod.xpath('.//div[@class="reviews"]/span[@class="no"]/text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url, max_age=0), process_product, dict(context, name=name, manufacturer=manufacturer, prod_id=prod_id, url=url))

    next_page = context.get('page', 1) + 1
    offset = context.get('offset', 0) + 24
    if prods:
        next_url = context['prods_url'] + '?layout=pfour_products&page=' + str(next_page) + '&skip=' + str(offset)
        session.queue(Request(next_url, max_age=0), process_prodlist, dict(context, page=next_page, offset=offset))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['prod_id']
    product.sku = product.ssid
    product.manufacturer = context['manufacturer']
    product.category = context['cat']

    prod_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        sku = prod_json.get('sku')
        if sku:
            product.sku = sku.split('-')[0]

    ean = data.xpath('//div[text()="EAN"]/following-sibling::div/text()').string()
    if ean:
        ean = ean.split(',')[0]
        if ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_key = data.xpath('//form/@data-prodid-selected').string()
    data_url = 'https://js.testfreaks.com/onpage/parfym-se/reviews.json?key=' + revs_key
    session.do(Request(data_url, force_charset='utf-8', max_age=0), process_getrevsurl, dict(product=product))


def process_getrevsurl(data, context, session):
    data_json = simplejson.loads(data.content)

    revs_url = data_json.get('your_review_url')
    session.do(Request(revs_url, force_charset='utf-8', max_age=0), process_reviews, dict(context))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('reviews', [])
    for rev in revs:
        if rev.get('lang') != 'sv':
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.get('date')

        author = rev.get('author')
        if author:
            author = remove_emoji(author).strip(' .+-')
            if len(author) > 2:
                review.authors.append(Person(name=author, ssid=author))
            else:
                author = None

        grade_overall = rev.get('score')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('verified_buyer')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('votes_up')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('votes_down')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        excerpt = rev.get('extract')
        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').replace('\r', '').strip(' •+-')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    next_url = revs_json.get('next_page_url')
    if next_url:
        session.do(Request(next_url, force_charset='utf-8', max_age=0), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
