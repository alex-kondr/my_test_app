from agent import *
from models.products import *
import simplejson
import re
import time
import random


XCAT = ['Brand', 'Australian Stocks', 'SIMs', 'Clearance', 'Refurbished', 'Deals']


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


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://buymobile.com.au/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    cats = data.xpath('//ul[li[contains(., "All Categories")]]//div[@class="panel__wrapper"]/ul/li[1]')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('following-sibling::li[1]/a/@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_prodlist, dict(cat=name))

    cats = data.xpath('//ul[li[contains(., "All Categories")]]//div[@class="panel"]//ul/li/a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    prods = data.xpath('//div[contains(@class, "product-card__info")]')
    for prod in prods:
        name = prod.xpath('.//span[contains(@class, "title")]/a/text()').string()
        url = prod.xpath('.//span[contains(@class, "title")]/a/@href').string().split('?')[0]

        revs_cnt = prod.xpath('.//div[contains(@class, "badge")]/@data-number-of-reviews').string()
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']

    prod_json = data.xpath('''//script[contains(., '"@type":"Brand"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.ssid = prod_json.get('productGroupID')
        product.manufacturer = prod_json.get('brand', {}).get('name')

    prod_json = data.xpath('''//script[contains(., ',"barcode":"') and not(contains(., 'variants'))]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.sku = str(prod_json.get('id'))

        mpn = prod_json.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('barcode')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    if product.ssid:
        revs_url = 'https://api.judge.me/reviews/reviews_for_widget?url=buymobilerapidco.myshopify.com&shop_domain=buymobilerapidco.myshopify.com&platform=shopify&page=1&per_page=5&product_id={}'.format(product.ssid)
        session.do(Request(revs_url, max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context["product"]

    json = simplejson.loads(data.content)
    html = data.parse_fragment(json.get("html", ''))

    revs = html.xpath("//div[@class='jdgm-rev jdgm-divider-top']")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath(".//@data-review-id").string()

        date = rev.xpath(".//span[@class='jdgm-rev__timestamp jdgm-spinner']/@data-content").string()
        if date:
            review.date = date.split(" ")[0]

        author = rev.xpath(".//span[@class='jdgm-rev__author']/text()").string()
        if author and author != 'null':
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath(".//span/@data-score").string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('@data-verified-buyer').string()
        if is_verified == 'true':
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.xpath('@data-thumb-up-count').string()
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('@data-thumb-down-count').string()
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.xpath(".//b[@class='jdgm-rev__title']//text()").string()
        excerpt = rev.xpath(".//div[@class='jdgm-rev__body']//text()").string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip(' -.+*')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    next_url = html.xpath('//a[@rel="next"]')
    if next_url:
        next_page = context.get("page", 1) + 1
        revs_url = 'https://api.judge.me/reviews/reviews_for_widget?url=buymobilerapidco.myshopify.com&shop_domain=buymobilerapidco.myshopify.com&platform=shopify&page={}&per_page=10&product_id={}'.format(next_page, product.ssid)
        session.do(Request(revs_url, max_age=0), process_reviews, dict(product=product, page=next_page))

    elif product.reviews:
        session.emit(product)