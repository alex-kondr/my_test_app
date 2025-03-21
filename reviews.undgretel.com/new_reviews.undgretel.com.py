from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Gutscheine', 'Tester', 'Show all']


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
    session.queue(Request('https://undgretel.com/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//span[contains(., "Products")]/following-sibling::ul[1]//a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat='Beauty' + '|' + name))


def process_prodlist(data, context, session):
    prods = data.xpath('//a[contains(@class, "group uppercase")]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

# no next page


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="product-id"]/@value').string()
    product.sku = data.xpath('//input[@class="product-variant-id"]/@value').string()
    product.category = context['cat']
    product.manufacturer = 'UND GRETEL'

    revs_cnt = data.xpath('//div/text()[contains(., "Reviews")]').string()
    if revs_cnt and int(revs_cnt.replace('Reviews', '').replace('.', '')) > 0:
        revs_url = 'https://judge.me/reviews/reviews_for_widget?url=undgretel.myshopify.com&shop_domain=undgretel.myshopify.com&platform=shopify&page=1&per_page=10&product_id={}'.format(product.ssid)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    new_data = data.parse_fragment(revs_json.get('html'))

    revs = new_data.xpath('//div[@data-review-id]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@data-review-id').string()

        date = rev.xpath('.//span/@data-content').string()
        if date:
            review.date = date.split()[0]

        author = rev.xpath('.//span[@class="jdgm-rev__author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        is_verified_buyer = rev.xpath('.//span[@class="jdgm-rev__buyer-badge"]')
        if is_verified_buyer:
            review.add_property(type="is_verified_buyer", value=True)

        grade_overall = rev.xpath('.//span/@data-score').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.xpath('.//b[@class="jdgm-rev__title"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//div[@class="jdgm-rev__body"]//text()').string(multiple=True)
        if excerpt and len(remove_emoji(excerpt).strip(' +-.')) > 2:
            if title:
                review.title = remove_emoji(title)
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip(' +-.')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    next_page = new_data.xpath('//a[@rel="next"]/@data-page').string()
    if next_page:
        next_url = 'https://judge.me/reviews/reviews_for_widget?url=undgretel.myshopify.com&shop_domain=undgretel.myshopify.com&platform=shopify&page={next_page}&per_page=10&product_id={ssid}'.format(next_page=next_page, ssid=product.ssid)
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product))

    elif product.reviews:
        session.emit(product)
