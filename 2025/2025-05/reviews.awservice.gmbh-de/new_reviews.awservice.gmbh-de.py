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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://awservice.gmbh', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('''//div[@data-settings='{"position":"absolute"}']''')
    for cat in cats:
        name = cat.xpath('div//span[@class="elementor-button-text"]/text()').string(multiple=True)

        sub_cats = cat.xpath('.//li/a')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('.//text()').string(multiple=True)
            url = sub_cat.xpath('@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//li[contains(@class, "product type-product")]')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('h2/text()').string()
        product.ssid = prod.xpath('.//@data-sku').string().replace(u'\u2011', '-')
        product.sku = product.ssid
        product.url = prod.xpath('a/@href').string()
        product.category = context['cat']

        prod_id = ''.join(['3' + numb for numb in product.sku]).replace('3 ', '20').replace('3-', '2d')
        url = 'https://integrations.etrusted.com/feeds/product-reviews/v1/channels/chl-37a24b53-a99a-4844-8ca3-e01f8c350e84/sku/{prod_id}/default/all/feed.json'.format(prod_id=prod_id)

        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_reviews(data, context, session):
    product = context['product']

    revs = simplejson.loads(data.content)
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.ssid = rev.get('id')
        review.url = product.url

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
        if not excerpt or len(excerpt.replace('\n', '').strip(' +-*.')) < 2:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').strip(' +-*.')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
