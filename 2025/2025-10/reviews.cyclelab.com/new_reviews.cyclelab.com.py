from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Pre-Owned Bikes', 'Other']


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
    session.queue(Request('https://www.cyclelab.com/', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats1 = data.xpath('//ul[@class="navbar-nav mr-auto"]/li')
    for cat1 in cats1:
        name1 = cat1.xpath('a/text()').string()

        if name1 not in XCAT:
            cats2 = cat1.xpath('.//ul[@class="nav flex-column"]/li')
            for cat2 in cats2:
                name2 = cat2.xpath('a/text()').string().split('">')[-1]
                if name2 in XCAT:
                    name2 = ''

                cats3 = cat2.xpath('ul/li/a')
                for cat3 in cats3:
                    name3 = cat3.xpath('text()').string()
                    url = cat3.xpath('@href').string()
                    if url:
                        cat = (name1 + '|' + name2 + '|' + name3).replace('||', '|')
                        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_category, dict(url=url, cat=cat))


def process_category(data, context, session):
    cat_name = data.xpath('//input[@id="category"]/@value').string()
    sub_cat_id = data.xpath('//input[@id="sub_category_id"]/@value').string()
    sub_cats_id = data.xpath('//input[@id="sub_categories_id"]/@value').string()
    if cat_name and sub_cat_id and sub_cats_id:
        url = 'https://www.cyclelab.com/products_ajax_call?page=&category={}&sub_category_id={}&sub_categories_id={}'.format(cat_name, sub_cat_id, sub_cats_id)
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(context, prods_url=url))


def process_prodlist(data, context, session):
    try:
        prods_json = simplejson.loads(data.content)
    except:
        return

    prods_html = data.parse_fragment(prods_json.get('output_data').replace('<!--', '').replace('-->', ''))
    prods = prods_html.xpath('//div[@class="item product product-item"]')
    for prod in prods:
        name = prod.xpath('.//a[@class="product-item-link"]/text()').string()
        url = prod.xpath('.//a[@class="product-item-link"]/@href').string()

        is_revs = prod.xpath('.//input[@class="all_product_ratting_value"]/@value').string()
        if is_revs and float(is_revs) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, url=url, name=name))

    pagination_html = data.parse_fragment(prods_json.get('pagination_links'))
    is_next_page = pagination_html.xpath('.//a[contains(., "Next")]')
    if is_next_page:
        next_page = context.get('page', 1) + 1
        next_url = context['prods_url'].split('page=')
        next_url = 'page={}'.format(next_page).join(next_url)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(context, page=next_page))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div[contains(@class, "Deatils-Box-Buttons cartButton")]//@id').string()
    product.sku = data.xpath('//span[@id="pro_plu"]/text()').string()
    product.category = context['cat'].replace('||', '|')

    manufacturer = data.xpath('//script[contains(., "item_brand:")]/text()').string()
    if manufacturer:
        manufacturer = manufacturer.split('item_brand: "')[-1].split('",')[0]
        if manufacturer and 'na' not in manufacturer.lower():
            product.manufacturer = manufacturer

    if product.ssid:
        rev_url = 'https://www.cyclelab.com/{}/reviews?page=1'.format(product.ssid)
        options = """-H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0' -H 'Accept: */*' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br' -H 'X-Requested-With: XMLHttpRequest' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin'"""
        session.do(Request(rev_url, use='curl', options=options, force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    try:
        revs_json = simplejson.loads(data.content)
    except:
        return      # https://www.cyclelab.com/product/1016637-bike-road-carb-orbea-orca-m40-my22 — Error 500

    revs = revs_json.get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.date = rev.get('date')

        author = rev.get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade = rev.get('rating')
        if grade:
            review.grades.append(Grade(type="overall", value=float(grade), best=5.0))

        excerpt = rev.get('review')
        if excerpt:
            excerpt = remove_emoji(excerpt).replace('<br />', '').replace('\n', '').replace('\r', '').strip()
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    revs_cnt = revs_json.get('total')
    offset = context.get('offset', 0) + 3
    if revs_cnt and int(revs_cnt) > offset:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.cyclelab.com/{}/reviews?page={}'.format(product.ssid, next_page)
        options = """-H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0' -H 'Accept: */*' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br' -H 'X-Requested-With: XMLHttpRequest' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin'"""
        session.do(Request(next_url, use='curl', options=options, force_charset='utf-8', max_age=0), process_reviews, dict(product=product, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
