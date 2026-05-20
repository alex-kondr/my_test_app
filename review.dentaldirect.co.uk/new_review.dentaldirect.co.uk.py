from agent import *
from models.products import *
import simplejson
import time
import random


XCAT = ['By Brand', 'View All', 'Brands']


def run(context, session):
    session.queue(Request('https://www.dentaldirect.co.uk/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    time.sleep(random.uniform(1, 3))

    cats = data.xpath('//ul[contains(@class, "level-1")]/li')
    for cat in cats:
        name = cat.xpath('a/span//text()').string()

        if name and name not in XCAT:
            subcats = cat.xpath('.//ul[contains(@class, "level-2")]/li/a')
            for subcat in subcats:
                url = subcat.xpath('@href').string()
                subcat_name = subcat.xpath('text()').string()

                if subcat_name not in XCAT:
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + subcat_name))


def process_prodlist(data, context, session):
    time.sleep(random.uniform(1, 3))

    prods = data.xpath('//div[@data-product-item]')
    for prod in prods:
        name = prod.xpath('.//p[@class="product-card--title"]/text()').string()
        link = prod.xpath('.//a[@class="product-card--title-link"]/@href').string().split("/")[-1]
        url = 'https://www.dentaldirect.co.uk/products/' + link
        ssid = prod.xpath('.//div/@data-oke-reviews-product-id').string()

        revs_count = prod.xpath('.//span[@class="oke-sr-count-number"]/text()').string()
        if revs_count and int(revs_count) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, ssid=ssid, url=url))


def process_product(data, context, session):
    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid'].split('-')[-1]
    product.sku = data.xpath('(//tr/@data-variant-sku)[1]').string()
    product.category = context['cat']

    try:
        product_json = simplejson.loads(data.xpath('''//script[contains(text(), '"gtin')]//text()''').string())

        if not product.sku:
            product.sku = product_json.get('sku')

        ean = product_json.get('offers', [{}])[0].get('gtin12', product_json.get('offers', [{}])[0].get('gtin13'))
        if ean:
            product.add_property(type='id.ean', value=ean)
    except:
        pass

    revs_url = "https://5i27ysv3j8.execute-api.us-west-2.amazonaws.com/prod/stores/d67635f6-ab51-496d-bcc0-d867216f0825/products/" + context['ssid'] + "/reviews?limit=5"
    session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    time.sleep(random.uniform(1, 3))

    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev['reviewId']

        date = rev.get('dateCreated')
        if date:
            review.date = date.split("T")[0]

        author = rev.get('reviewer', {}).get('displayName')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.get('helpfulCount')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('unhelpfulCount')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        is_recommended = rev.get('isRecommended')
        if is_recommended is True:
            review.add_property(value=True, type='is_recommended')

        is_verified_buyer = rev.get('reviewer', {}).get('isVerified')
        if is_verified_buyer is True:
            review.add_property(type='is_verified_buyer', value=True)

        title= rev.get('title')
        excerpt = rev.get('body')
        if excerpt and len(excerpt.replace('\n', '').replace('\r', '').strip()) > 2:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.replace('\n', '').replace('\r', '').replace(u'â€œ', u'"').replace(u'\x9D', '"').replace(u'â€˜', "'").strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    next_url = revs_json.get('nextUrl')
    if next_url:
        next_url = 'https://5i27ysv3j8.execute-api.us-west-2.amazonaws.com/prod' + next_url
        session.do(Request(next_url), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)



