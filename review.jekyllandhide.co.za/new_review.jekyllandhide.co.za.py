from agent import *
from models.products import *
import simplejson
import re
import time
import random


XCAT = ['View All', 'SHOP LUGGAGE', 'ALL FOOTWEAR', 'ALL LEATHER JACKETS']


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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.jekyllandhide.co.za/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    cats = data.xpath('//nav[@role="navigation"]/ul/li/details')
    for cat in cats:
        name = cat.xpath('summary//text()').string(multiple=True)

        cats1 = cat.xpath('.//div[@class="mega-menu__item"]')
        for cat1 in cats1:
            cat1_name = cat1.xpath('a/text()').string()
            if cat1_name in XCAT:
                cat1_name = ''

            subcats = cat1.xpath('ul/li/a')
            for subcat in subcats:
                subcat_name = subcat.xpath('.//text()').string(multiple=True)
                url = subcat.xpath('@href').string()

                if subcat_name not in XCAT:
                    session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    prods = data.xpath('//a[contains(@class, "product-card__title")]')
    for prod in prods:
        name = prod.xpath('.//text()').string(multiple=True)
        url = prod.xpath('@href').string().split('?')[0]
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//button[@type="load-more"]/@action').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="product-id"]/@value').string()
    product.category = context['cat'].replace('||', '|')

    try:
        prod_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')

        ean = prod_json.get('hasVariant', [{}])[0].get('gtin')
        if ean and str(ean).isdigit() and len(str(ean)) > 10:
            product.add_property(type='id.ean', value=ean)
    except:
        pass

    sku = data.xpath('//p[@class="product-sku"]/text()').string(multiple=True)
    if sku:
        sku = sku.replace('SKU:', '').strip()
        if len(sku) > 1:
            product.sku = sku

    revs_cnt = data.xpath('//div/@data-number-of-reviews').string()
    if revs_cnt and int(revs_cnt) > 0:
        revs_url = 'https://cdn.judge.me/reviews/reviews_for_widget?product_id={}&page=1&per_page=16&translation_locale=en&skip_other_languages=true&widget_theme=carousel&ts=2026-09-04T10%3A39%3A09Z&shop_domain=jekyll-and-hide-sa.myshopify.com&platform=shopify'.format(product.ssid)
        session.do(Request(revs_url), process_reviews, dict(product=product, revs_cnt=int(revs_cnt)))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    time.sleep(random.uniform(1, 3))

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

    revs_cnt = context['revs_cnt']
    offset = context.get('offset', 0) + 16
    if offset < revs_cnt:
        next_page = context.get('page', 1) + 1
        next_url = 'https://cdn.judge.me/reviews/reviews_for_widget?product_id={ssid}&page={page}&per_page=16&translation_locale=en&skip_other_languages=true&widget_theme=carousel&ts=2026-09-04T10%3A39%3A09Z&shop_domain=jekyll-and-hide-sa.myshopify.com&platform=shopify'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url), process_reviews, dict(context, product=product, offset=offset, page=next_page))

    elif product.reviews:
            session.emit(product)
