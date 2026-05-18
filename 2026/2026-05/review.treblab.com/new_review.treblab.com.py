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
    session.queue(Request('https://treblab.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[contains(@class, "invisible")]//ul[@class="mega-menu__nav grid"]/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//a[contains(@class, "product-card")]/@href')
    for prod in prods:
        url = prod.string()
        session.queue(Request(url), process_product, dict(context, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))

def process_product(data, context, session):
    product = Product()
    product.name = data.xpath('//h1[contains(@class, "title")]/text()').string()
    product.url = context['url']
    product.ssid = data.xpath('//product-info/@data-product-id|//input[@name="product-id"]/@value').string()
    product.sku = data.xpath('//input[@name="id"]/@value').string()
    product.category = context['cat']
    product.manufacturer = 'TREBLAB'

    prod_json = data.xpath('''//script[@id="web-pixels-manager-setup"]/text()''').string()
    if prod_json:

        mpn = prod_json.split(r',\"sku\":\"', 1)[-1].split(r'\",')[0]
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

    if product.ssid:
        revs_url = 'https://storefront.trustshop.io/storefront/reviews?product_id={}&type=all&per_page=6'.format(product.ssid)
        session.do(Request(revs_url, max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('data', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('id')

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('customer', {}).get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('star')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('buyer_verification')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('helpful')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        title = rev.get('title')
        excerpt = rev.get('content')
        if excerpt and len(remove_emoji(excerpt).replace('\n', '').strip(' .+-\t')) > 2:
            if title:
                review.title = remove_emoji(title).replace('\n', '').strip(' .+-\t')
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').strip(' .+-\t')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    next_revs = revs_json.get('next_cursor')
    if next_revs:
        next_page = context.get('page', 1) + 1
        next_url = 'https://storefront.trustshop.io/storefront/reviews?product_id={ssid}&type=all&current_page={page}&per_page=6'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url, max_age=0), process_reviews, dict(product=product, page=next_page))

    elif product.reviews:
        session.emit(product)
