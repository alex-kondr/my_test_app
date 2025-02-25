from agent import *
from models.products import *
import simplejson
import time


XCAT = ['plan_premium', 'plan_simo', 'device_faim', 'plan_sowo', 'prices', 'renewal']


def run(context, session):
    options = '-H "Accept: application/json, text/plain, */*" -H "Connection: keep-alive" -H "Host: api.bouyguestelecom.fr" -H "Referer: https://www.bouyguestelecom.fr" -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36 x-version: 3" -H "x-version: 3" -H "Content-Type: application/json; charset=utf-8"'
    session.queue(Request('https://api.bouyguestelecom.fr/ventes/mur-produits?type=accessory', use='curl', force_charset='utf-8', options=options, max_age=0), process_frontpage, {})
    session.queue(Request('https://api.bouyguestelecom.fr/ventes/mur-produits?type=phone', use='curl', force_charset='utf-8', options=options, max_age=0), process_frontpage, {})


def process_frontpage(data, context, session):
    resp = simplejson.loads(data.content)
    cats = resp.get('categories', [])
    for cat in cats:
        if cat and cat not in XCAT:
            prods = resp['categories'][cat].get('products', [])
            for prod in prods.values():
                product = Product()
                product.name = prod['name']

                manufacturer = prod.get('manufacturer_name')
                if manufacturer:
                    product.name = manufacturer + ' ' + product.name
                    product.manufacturer = manufacturer.replace('reconditionné', '')

                product.url = 'https://www.bouyguestelecom.fr{}'.format(prod['url'])
                product.category = resp['categories'][cat].get('name')
                product.ssid = str(prod['id'])

                ean = prod.get('product_gencode')   # Sometimes it's empty
                if ean:
                    ean = ean[0]
                    product.properties.append(ProductProperty(type='id.ean', value=str(ean)))

                revs_cnt = prod.get('bazaarvoice', {}).get('count')
                if revs_cnt and int(revs_cnt) > 0:
                    revs_url = 'https://awsapis3.netreviews.eu/product?idWebsite=d60655de-eefb-b8f4-1126-927316552252&query=reviews&plateforme=fr&product={}'.format(product.ssid)
                    session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product))

                if product.reviews:
                    session.emit(product)


def process_reviews(data, context, session):
    product = context['product']
    try:
        resp = simplejson.loads(data.content)
        if not resp:
            return  # It's empty sometimes
    except:
        return

    revs = resp[0].get('reviews', [])
    for rev in revs:
        review = Review()
        review.title = rev.get('product_review_title')
        review.url = product.url
        review.type = 'user'
        review.ssid = rev['id_review']

        date = rev.get('publish_date')
        if date:
            review.date = date.split()[0]

        author_name = rev.get('firstname')
        author_email = rev.get('email')
        if author_name and author_email:
            review.authors.append(Person(name=author_name, ssid=author_name, email=author_email))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        is_verified = rev.get('order_ref')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        grade_overall = rev.get('rate')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_recommended = rev.get('product_review_recommandation_ami')
        if is_recommended and is_recommended.lower() == 'oui':
            review.add_property(type='is_recommended', value=True)

        pros = rev.get('product_review_recommandation_telephone')
        if pros:
            pros = pros.split(', ')
            for pro in pros:
                review.properties.append(ReviewProperty(type='pros', value=pro))

        excerpt = rev.get('review')
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            product.reviews.append(review)
