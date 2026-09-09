from agent import *
from models.products import *
import time
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


def RequestProds(cat_id, page):
    timestamp_ms = int(time.time() * 1000)
    url = 'https://services.mybcapps.com/bc-sf-filter/filter?t={timestamp_ms}&_=pf&shop=uk-avon.myshopify.com&page={page}&limit=24&sort=manual&locale=en&event_type=collection&build_filter_tree=true&sid=c89b4436-651a-44ca-a894-6f6b1c93de69&pg=collection_page&zero_options=true&product_available=false&variant_available=false&sort_first=available&urlScheme=2&collection_scope={cat_id}'.format(cat_id=cat_id, page=page, timestamp_ms=timestamp_ms)
    r = Request(url)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(RequestProds('2073', 1), process_prodlist, dict(cat='Womens Fragrance', cat_id='2073'))
    session.queue(RequestProds('206749171757', 1), process_prodlist, dict(cat='Body Sprays', cat_id='206749171757'))
    session.queue(RequestProds('207334735917', 1), process_prodlist, dict(cat='Mens Fragrance', cat_id='207334735917'))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    try:
        prods_json = simplejson.loads(data.content)
    except:
        prods_json = {}

    prods = prods_json.get('products')
    for prod in prods:
        name = prod.get('title')
        subcat = prod.get('product_category', '')
        url = 'https://avon.uk.com/products/' + prod.get('handle')
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(cat=context['cat']+'|'+subcat, name=name, url=url))

    prods_cnt = context.get('prods_cnt', prods_json.get('total_product', 0))
    offset = context.get('offset', 0) + 24
    if offset < prods_cnt:
        next_page = context.get('page', 1) + 1
        session.queue(RequestProds(context['cat_id'], next_page), process_prodlist, dict(context, prods_cnt=prods_cnt, offset=offset, page=next_page))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="product-id"]/@value').string()
    product.category = context['cat'].strip(' |')

    try:
        prod_json = data.xpath('''//script[contains(., '"@type": "Product"')]/text()''').string()
        prod_json = simplejson.loads(prod_json)

        product.sku = prod_json.get('offers', {}).get('sku')
        product.manufacturer = prod_json.get('brand', {}).get('name')
    except:
        pass

    revs_url = 'https://cdn.judge.me/reviews/reviews_for_widget?product_id={}&page=1&sort_by=created_at&sort_dir=desc&skip_other_languages=true&widget_theme=standard&ts=2026-09-04T09%3A05%3A56Z&shop_domain=uk-avon.myshopify.com&platform=shopify'.format(product.ssid)
    session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data: Response, context: dict[str, str], session: Session):
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
        review.ssid = rev.get('uuid')

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('reviewer_name')
        if author and 'anonymous' not in author.lower():
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('verified_buyer')
        if is_verified_buyer is True:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('thumb_up')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('thumb_down')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        excerpt = rev.get('body_html')
        if excerpt:
            excerpt = remove_emoji(data.parse_fragment(excerpt).xpath('.//text()').string(multiple=True))
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = context.get('revs_cnt', revs_json.get('number_of_reviews', 0))
    offset = context.get('offset', 0) + 5
    if offset < revs_cnt:
        next_page = context.get('page', 1) + 1
        next_url = 'https://cdn.judge.me/reviews/reviews_for_widget?product_id={ssid}&page={page}&sort_by=created_at&sort_dir=desc&skip_other_languages=true&widget_theme=standard&ts=2026-09-04T09%3A05%3A56Z&shop_domain=uk-avon.myshopify.com&platform=shopify'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url), process_reviews, dict(product=product, revs_cnt=revs_cnt, offset=offset, page=next_page))

    elif product.reviews:
            session.emit(product)
