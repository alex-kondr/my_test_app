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
    cats1 = data.xpath('//li[contains(@class, "site-nav")][not(contains(@class, "grandchild"))]')
    for cat1 in cats1:
        name1 = cat1.xpath('a/text()').string().strip()

        cats2 = cat1.xpath('.//li[a[contains(., "Category")]]/ul//a')
        for cat2 in cats2:
            name2 = cat2.xpath('text()').string()
            url = cat2.xpath('@href').string()

            if 'All ' not in name2:
                session.queue(Request(url, force_charset='utf-8', use='curl'), process_prodlist, dict(cat=name1 + '|' + name2))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "grid-item small--one-half")]')
    for prod in prods:
        name = prod.xpath('p/text()').string()
        url = prod.xpath('a/@href').string()
        ssid = prod.xpath('span/@data-id').string()
        if name and url and ssid:
            url = 'https://www.avedastore.ie/collections/all-products/products/' + url.split('/')[-1]
            session.queue(Request(url, force_charset='utf-8', use='curl'), process_product, dict(context, name=name, url=url, ssid=ssid))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8', use='curl'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = 'Aveda'
    product.ssid = context['ssid']

    prod_json = data.xpath('//script[@id="ProductJson-product-template"]/text()').string()
    if prod_json:
        ean = simplejson.loads(prod_json).get('variants', [{}])[0].get('barcode')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    sku = data.xpath('//div[@class="trustpilot_review_container"]/div/@data-sku').string()
    if sku:
        product.sku = sku.split(',')[0]

        revs_url = 'https://widget.trustpilot.com/trustbox-data/5763bccae0a06d08e809ecbb?businessUnitId=6628178da21a8d427174cb34&locale=en-GB&sku={}&reviewsPerPage=10&reviewLanguages=en'.format(sku.replace(',', '%2C'))
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('importedProductReviews', {}).get('productReviews', []) + revs_json.get('productReviews', {}).get('reviews', [])
    for rev in revs:
        review = Review()
        review.url = product.url
        review.type = "user"

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

                review.ssid = rev.get('id')
                if not review.ssid:
                    review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if revs:
        next_page = context.get('page', 1) + 1
        revs_url = 'https://widget.trustpilot.com/trustbox-data/5763bccae0a06d08e809ecbb?businessUnitId=6628178da21a8d427174cb34&locale=en-GB&sku={sku}%2C1298%2C1299&reviewsPerPage=10&reviewLanguages=en&page={page}'.format(sku=product.sku.replace(',', '%2C'), page=next_page)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, page=next_page))

    elif product.reviews:
        session.emit(product)
