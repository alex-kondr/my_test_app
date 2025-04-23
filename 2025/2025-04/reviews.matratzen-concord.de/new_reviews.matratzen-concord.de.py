from agent import *
from models.products import *
import simplejson
import re


SKU_CODE = []


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
    session.queue(Request('https://www.matratzen-concord.de/', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[div[regexp:test(@title, "Nach Material|Nach Sortiment")]]')
    for cat in cats:
        name = cat.xpath('div//a[contains(., "Alle ")]//text()').string(multiple=True).replace('Alle ', '').strip()

        sub_cats = cat.xpath('div//a[not(contains(., "Alle "))]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('.//text()').string(multiple=True)
            url = sub_cat.xpath('@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name + '|' + sub_name))
        else:
            url = cat.xpath('div//a[contains(., "Alle ")]/@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-info"]')
    for prod in prods:
        name = prod.xpath('a/text()').string()
        url = prod.xpath('a/@href').string().split('?')[0]

        revs = prod.xpath('div[@class="product-rating"]')
        if revs:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url))

    next_page = data.xpath('//input[@id="p-next-bottom" and not(@disabled)]/@value').string()
    if next_page:
        next_url = data.response_url.split('?')[0] + '?p=' + next_page
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//meta[@itemprop="gtin13"]/@content').string() or product.url.split('/')[-1]
    product.sku = product.url.split('/')[-1]
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[@itemprop="name"]/@content').string()

    mpn = data.xpath('//etrusted-widget/@data-sku').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

        sku_code = ''
        for char in mpn:
            sku_code += hex(ord(char))[2:]

        if sku_code not in SKU_CODE:
            SKU_CODE.append(sku_code)

            revs_url = 'https://integrations.etrusted.com/feeds/product-reviews/v1/channels/chl-cf9b6dac-2f0c-4154-b67d-ff6ee8f037bf/sku/{}/default/all/feed.json'.format(sku_code)
            session.do(Request(revs_url), process_reviews, dict(product=product))


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
        if excerpt and len(remove_emoji(excerpt).strip(' .+-')) > 2:
            if title:
                review.title = remove_emoji(title).strip(' .+-\n\t')
        else:
            excerpt  = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').strip(' .+-\n\t')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
