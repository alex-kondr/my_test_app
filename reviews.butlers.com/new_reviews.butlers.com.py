from agent import *
from models.products import *
import simplejson


XCATS = ['BUTLERS', 'Marken', 'Shop the Look', 'Beratung', 'Stores', 'Sale']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
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

                    if sub_name and 'Alle' not in sub_name:
                        sub_cats1 = sub_cat.get('children')
                        if sub_cats1:
                            for sub_cat1 in sub_cats1:
                                sub_name1 = sub_cat1.get('name')
                                url = sub_cat1.get('href')

                                if sub_name1 and 'Alle' not in sub_name1:
                                    session.queue(Request(url + '?order=AVERAGE_RATING'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                        else:
                            url = sub_cat.get('href')
                            session.queue(Request(url + '?order=AVERAGE_RATING'), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    cat_id = context.get('cat_id')
    prods_url = 'https://www.home24.de/graphql?extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%224c0db1839cdad663e84602f7172cfc894d8201a350ea42308caad436f056238e%22%7D%7D&variables=%7B%22urlParams%22%3A%22order%3DAVERAGE_RATING%22%2C%22locale%22%3A%22de_DE%22%2C%22first%22%3A120%2C%22offset%22%3A{offset}%2C%22id%22%3A%22{cat_id}%22%2C%22format%22%3A%22WEBP%22%2C%22sortingScore%22%3A%22A%22%2C%22userIP%22%3A%22%22%2C%22userAgent%22%3A%22Mozilla%2F5.0+%28Windows+NT+10.0%3B+Win64%3B+x64%3B+rv%3A121.0%29+Gecko%2F20100101+Firefox%2F121.0%22%2C%22backend%22%3A%22ThirdParty%22%2C%22thirdPartyClientId%22%3A%22211a0ad7-10da-42a7-9b3f-fc44b6737763%22%2C%22thirdPartySessionId%22%3A%226%22%7D'

    if cat_id:
        prods = simplejson.loads(data.content).get('data', {}).get('categories', {})[0].get('categoryArticles', {}).get('articles')
        for prod in prods:
            name = prod.get('name')
            url = 'https://www.home24.de/' + prod.get('url')

            revs_cnt = prod.get('ratings', {}).get('count')
            if revs_cnt and int(revs_cnt) > 0:
                session.queue(Request(url), process_product, dict(context, name=name, url=url))
            else:
                return

        offset = context.get('offset', 0) + 120
        if offset < context['prods_cnt']:
            session.queue(Request(prods_url.format(cat_id=cat_id, offset=offset)), process_prodlist, dict(context))
    else:
        cat_id = data.xpath('//div/@data-cnstrc-filter-value').string()
        prods_cnt = data.xpath('//div/@data-cnstrc-num-results').string()
        session.queue(Request(prods_url.format(cat_id=cat_id, offset=0)), process_prodlist, dict(context, cat_id=cat_id, prods_cnt=int(prods_cnt)))


def process_product(data,context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1]
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
        options = '''-X POST -H 'content-type: application/json' --data-raw '{"query":"query ProductReviews($sku:String! $locale:Locale! $limit:Int! $offset:Int!){articles(skus:[$sku],locale:$locale){reviews(limit:$limit,offset:$offset){title name message rating date city isTranslation}}}","variables":{"sku":"''' + product.sku + """","locale":"de_DE","limit":100,"offset":0}}'"""
        session.do(Request('https://www.home24.de/graphql', use='curl', force_charset='utf-8', max_age=0, options=options), process_reviews, dict(product=product, revs_cnt=int(revs_cnt)))


def process_reviews(data, context, session):
    product = context['product']

    revs = simplejson.loads(data.content).get('data', {}).get('articles', {})[0].get('reviews')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('date')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.get('title')
        excerpt = rev.get('message')
        if excerpt:
            review.title = title
        elif title:
            excerpt = title

        if excerpt:
            excerpt = excerpt.replace('\r', '').replace('\n', '')
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    offset = context.get('offset', 0) + 100
    if offset < context['revs_cnt']:
        options = '''-X POST -H 'content-type: application/json' --data-raw '{"query":"query ProductReviews($sku:String! $locale:Locale! $limit:Int! $offset:Int!){articles(skus:[$sku],locale:$locale){reviews(limit:$limit,offset:$offset){title name message rating date city isTranslation}}}","variables":{"sku":"''' + product.sku + '''","locale":"de_DE","limit":100,"offset":''' + str(offset) + """}}'"""
        session.do(Request('https://www.home24.de/graphql', use='curl', force_charset='utf-8', max_age=0, options=options), process_reviews, dict(context, product=product, offset=offset))

    elif product.reviews:
        print('emit')
        session.emit(product)
