from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Sale']


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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.matratzen-concord.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@data-flyout-menu-id]/div[@class="container"]')
    for cat in cats:
        name = cat.xpath('.//div[@class="navigation-flyout-category-link"]/a/@title').string()

        if name not in XCAT:
            sub_cats = cat.xpath('.//div[@class="col-3 navigation-flyout-col"]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('div[contains(@class, "level-0")]//text()').string(multiple=True)

                sub_cats1 = sub_cat.xpath('.//a[contains(@class, "level-1")]')
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('.//text()').string(multiple=True)
                    url = sub_cat1.xpath('@href').string()

                    if not sub_name1.startswith("All"):
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-info"]')
    for prod in prods:
        name = prod.xpath('a/text()').string()
        url = prod.xpath('a/@href').string()

        revs = prod.xpath('div[@class="product-rating"]')
        if revs:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    prods_cnt = data.xpath('//div/@data-product-count').string()
    offset = context.get('offset', 0) + 15
    if prods_cnt and offset < int(prods_cnt):
        next_page = context.get('page', 1) + 1
        next_url = data.response_url.split('?')[0] + '?p=' + str(next_page)
        session.queue(Request(next_url), process_prodlist, dict(context, page=next_page, offset=offset))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[@itemprop="name"]/@content').string()

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    mpn = data.xpath('//etrusted-widget/@data-sku').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

        sku_code = ''
        for char in mpn:
            sku_code += hex(ord(char))[2:]

        revs_url = 'https://integrations.etrusted.com/feeds/product-reviews/v1/channels/chl-cf9b6dac-2f0c-4154-b67d-ff6ee8f037bf/sku/{}/default/all/feed.json'.format(sku_code)
        session.queue(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = simplejson.loads(data.content) or []
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('id').replace('rev-', '')

        date = rev.get('submittedAt')
        if date:
            review.date = date.split('T')[0]

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('isVerified')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('title')
        excerpt = rev.get('comment')
        if excerpt and len(remove_emoji(excerpt).strip(' .+-')) > 1:
            if title:
                review.title = remove_emoji(title).strip(' .+-\n\t')
        else:
            excerpt  = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').strip(' .+-\n\t')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
