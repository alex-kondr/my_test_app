from agent import *
from models.products import *
import simplejson


XCATS = ['BUTLERS', 'Marken', 'Shop the Look', 'Beratung', 'Stores', 'Sale']


def run(context, session):
    session.queue(Request('https://www.home24.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats_json = data.xpath('//div/@data-initial-state[contains(., "Menü")]').string()
    if cats_json:

        cats = simplejson.loads(cats_json).get('navigation', {}).get('children')
        for cat in cats:
            name = cat.get('name')

            if name not in XCATS:
                sub_cats = cat.get('children', {})
                for sub_cat in sub_cats:
                    sub_name = sub_cat.get('name')

                    if 'Alle' not in sub_name:
                        sub_cats1 = sub_cat.get('children')
                        if sub_cats1:
                            for sub_cat1 in sub_cats1:
                                sub_name1 = sub_cat1.get('name')
                                url = sub_cat1.get('href')

                                if 'Alle' not in sub_name1:
                                    session.queue(Request(url + '?order=AVERAGE_RATING'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                        else:
                            url = sub_cat.get('href')
                            session.queue(Request(url + '?order=AVERAGE_RATING'), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('').string()
    for prod in prods:
        pass


def process_product(data,context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('')
    product.category = context['cat']

    prod_json = data.xpath('//script[@type="application/ld+json" and contains(., "Product")]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)
        product.sku = prod_json.get('sku')
        product.manufacturer = prod_json.get('brand', {}).get('name')

        ean = prod_json.get('gtin')
        if ean:
            product.add_property(type='id.ean', value=ean)

        revs_cnt = prod_json.get('aggregateRating', {}).get('reviewCount')
        options = '''-X POST -H 'content-type: application/json' --data-raw '{"query":"query ProductReviews($sku:String! $locale:Locale! $limit:Int! $offset:Int!){articles(skus:[$sku],locale:$locale){reviews(limit:$limit,offset:$offset){title name message rating date city isTranslation}}}","variables":{"sku":"''' + product.sku + """","locale":"de_DE","limit":50,"offset":0}}'"""
        session.queue(Request('https://www.home24.de/graphql', use='curl', forse_charset='utf-8', options=options), process_reviews, dict(product=product, revs_cnt=revs_cnt))


def process_reviews(data, context, session):
    product = context['product']

    revs = simplejson.loads(data.content).get('data', {}).get('articles', {})[0].get('reviews')
    for rev in revs:
        review = Review()
        review.type = 'user'

        date = rev.get('date')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(typr='overall', value=float(grade_overall), best=5.0))

        title = rev.get('title')
        excerpt = rev.get('message')
        if excerpt:
            review.title = title
        elif title:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    offset = context.get('offcet', 0) + 50
    if offset < context['revs_cnt']:
        options = '''-X POST -H 'content-type: application/json' --data-raw '{"query":"query ProductReviews($sku:String! $locale:Locale! $limit:Int! $offset:Int!){articles(skus:[$sku],locale:$locale){reviews(limit:$limit,offset:$offset){title name message rating date city isTranslation}}}","variables":{"sku":"''' + product.sku + """","locale":"de_DE","limit":50,"offset":""" + str(offset) + """}}'"""
        session.queue(Request('https://www.home24.de/graphql', use='curl', forse_charset='utf-8', options=options), process_reviews, dict(context, offset=offset))

    elif product.reviews:
        session.emit(product)
