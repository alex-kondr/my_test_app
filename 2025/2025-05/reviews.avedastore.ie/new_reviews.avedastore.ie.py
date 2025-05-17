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
    session.queue(Request('https://www.avedastore.ie/', force_charset='utf-8', use='curl'), process_frontpage, {})


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@data-title]')
    for cat in cats:
        name = cat.xpath('text()').string(multiple=True)

        sub_cats = cat.xpath('ul/li[contains(., "Category")]//li/a')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = sub_cat.xpath('@href').string()

            if 'All ' not in sub_name:
                session.queue(Request(url, force_charset='utf-8', use='curl'), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-card__info")]')
    for prod in prods:
        name = prod.xpath('.//a[contains(@class, "title")]/text()').string()
        url = prod.xpath('.//a[contains(@class, "title")]/@href').string()

        rating = prod.xpath('div[contains(@class, "rating")]')
        if rating:
            session.queue(Request(url, force_charset='utf-8', use='curl'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8', use='curl'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = 'Aveda'

    prod_json = data.xpath('''//script[@type="application/json" and contains(., '"sku":"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.ssid = str(prod_json.get('id'))
        product.sku = str(prod_json.get('sku'))

        revs_url = 'https://widget.trustpilot.com/trustbox-data/5763bccae0a06d08e809ecbb?businessUnitId=6628178da21a8d427174cb34&locale=en-GB&sku={}&reviewsPerPage=10&reviewLanguages=en'.format(product.sku)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('importedProductReviews', {}).get('productReviews', []) + revs_json.get('productReviews', {}).get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.ssid = rev.get('id')

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('consumer', {}).get('displayName')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('stars')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        grades = rev.get('attributeRatings', [])
        for grade in grades:
            grade_name = grade.get('name')
            grade_val = grade.get('rating')
            if grade_name and grade_val:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

        is_verified = rev.get('source', {}).get('name')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.get('content')
        if excerpt:
            excerpt = remove_emoji(excerpt.replace('\n', '')).strip(' .+-')
            if len(excerpt) > 1:
                review.add_property(type="excerpt", value=excerpt)

                product.reviews.append(review)

    if revs:
        next_page = context.get('page', 1) + 1
        revs_url = 'https://widget.trustpilot.com/trustbox-data/5763bccae0a06d08e809ecbb?businessUnitId=6628178da21a8d427174cb34&locale=en-GB&sku={sku}%2C1298%2C1299&reviewsPerPage=10&reviewLanguages=en&page={page}'.format(sku=product.sku, page=next_page)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, page=next_page))

    elif product.reviews:
        session.emit(product)
