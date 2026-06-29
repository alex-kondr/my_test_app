from agent import *
from models.products import *
import simplejson
import base64


XCAT = ['Wohnbereiche', 'Wohnideen', 'SALE', 'Marken', 'Prospekte', 'Gutscheine', 'Wohnbereiche', 'Küchenstudio', 'Planung und Beratung']


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.roller.de/api/navigation/desktop', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    try:
        cats_json = simplejson.loads(data.content)
    except:
        return

    for cat in cats_json:
        name = cat.get('text')

        if name not in XCAT:
            cats1 = cat.get('subLinks', [])
            for cat1 in cats1:
                cat1_name = cat1.get('text')

                if cat1_name not in XCAT:
                    subcats = cat1.get('subLinks', [])
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.get('text')
                            cat_id = base64.b64decode(subcat.get('url')).decode('utf-8').split('/')[-2]
                            url = 'https://www.roller.de/api/category/{}/products?sort=topRated'.format(cat_id)

                            if subcat_name not in XCAT:
                                session.queue(Request(url, force_charset='utf-8'), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name, cat_url=url))
                    else:
                        cat_id = cat1.get('url').split('/')[-2]
                        url = 'https://www.roller.de/api/category/{}/products?sort=topRated'.format(cat_id)
                        session.queue(Request(url, force_charset='utf-8'), process_prodlist, dict(cat=name+'|'+cat1_name, cat_url=url))


def process_prodlist(data, context, session):
    try:
        prods_json = simplejson.loads(data.content)
    except:
        prods_json = {}

    prods = prods_json.get('products', [])
    for prod in prods:
        product = Product()
        product.name = prod.get('name')
        product.ssid = str(prod['code'])
        product.url = 'https://www.roller.de/' + product.ssid
        product.sku = product.ssid
        product.category = context['cat']
        product.manufacturer = prod.get('brandName')

        revs_cnt = prod.get('rating', {}).get('count')
        if revs_cnt and int(revs_cnt) > 0:
            revs_url = 'https://www.roller.de/api/products/' + product.ssid + '/reviews?page=0'
            session.queue(Request(revs_url, force_charset='utf-8'), process_reviews, dict(product=product, revs_cnt=int(revs_cnt)))
        else:
            return

    prods_cnt = context.get('prods_cnt', prods_json.get('pagination', {}).get('totalResults', 0))
    offset = context.get('offset', 0) + 36
    if offset < prods_cnt:
        next_page = context.get('page', 0) + 1
        next_url = context['cat_url'] + '&page=' + str(next_page)
        session.queue(Request(next_url, force_charset='utf-8'), process_prodlist, dict(context, page=next_page, prods_cnt=prods_cnt, offset=offset))


def process_reviews(data, context, session):
    product = context['product']

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('comments', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        # no author

        date = rev.get('date')
        if date:
            review.date = date.split('T')[0]

        grade_overall = rev.get('rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('comment')
        if excerpt:
            excerpt = excerpt.replace('\n', '').strip(' ,=+-"*\n')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 8
    if offset < context['revs_cnt']:
        next_page = context.get('page', 0) + 1
        next_url = 'https://www.roller.de/api/products/' + product.ssid + '/reviews?page=' + str(next_page)
        session.do(Request(next_url, force_charset='utf-8'), process_reviews, dict(context, product=product, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
