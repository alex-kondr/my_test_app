from agent import *
from models.products import *
import simplejson


XCAT = ['Reacondicionados', 'Servicio técnico', 'Servicios']


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.phonehouse.es/api/catalog_system/pub/category/tree/3', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    try:
        cats = simplejson.loads(data.content)
    except:
        return

    for cat in cats:
        name = cat.get('name')

        if name and name not in XCAT:
            cats1 = cat.get('children', [])
            if cats1:
                for cat1 in cats1:
                    cat1_name = cat1.get('name')

                    subcats = cat1.get('children', [])
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.get('name')
                            cat_id = subcat.get('id')
                            url = 'https://www.phonehouse.es/api/catalog_system/pub/products/search?fq=C:/{}/&_from=0&_to=49'.format(cat_id)
                            session.queue(Request(url, force_charset='utf-8'), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name, cat_id=cat_id))
                    else:
                        cat_id = cat1.get('id')
                        url = 'https://www.phonehouse.es/api/catalog_system/pub/products/search?fq=C:/{}/&_from=0&_to=49'.format(cat_id)
                        session.queue(Request(url, force_charset='utf-8'), process_prodlist, dict(cat=name+'|'+cat1_name, cat_id=cat_id))
            else:
                cat_id = cat.get('id')
                url = 'https://www.phonehouse.es/api/catalog_system/pub/products/search?fq=C:/{}/&_from=0&_to=49'.format(cat_id)
                session.queue(Request(url, force_charset='utf-8'), process_prodlist, dict(cat=name, cat_id=cat_id))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    try:
        prods = simplejson.loads(data.content)
    except:
        prods = []

    for prod in prods:
        product = Product()
        product.name = prod.get('productName')
        product.url = prod.get('link')
        product.ssid = prod.get('productId')
        product.sku = prod.get('items', [{}])[0].get('itemId')
        product.category = context['cat']
        product.manufacturer = prod.get('brand')

        mpn = prod.get('items', [{}])[0].get('referenceId', [{}])[0].get('Value')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod.get('items', [{}])[0].get('ean')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

            url = 'https://media.flixcar.com/modular/web-api/es/731/{ean}d3d3LnBob25laG91c2UuZXM/t.json?mpn=&ean={ean}&distId=731&iso=es&flIso=en'.format(ean=ean)
            session.queue(Request(url, force_charset='utf-8'), process_product, dict(context, product=product))

    if len(prods) == 50:
        offset = context.get('offset', 0) + 50
        if offset < 2500:
            next_url = 'https://www.phonehouse.es/api/catalog_system/pub/products/search?fq=C:/{}/&_from={}&_to={}'.format(context['cat_id'], offset, offset + 49)
            session.queue(Request(next_url, force_charset='utf-8'), process_prodlist, dict(context, offset=offset))


def process_product(data: Response, context: dict[str, str], session: Session):
    try:
        rev_mod = simplejson.loads(data.content)[0].get('modules', {}).get('reviews', {})
    except:
        return

    prod_id = rev_mod.get('product_id')
    store_id = rev_mod.get('store')
    revs_cnt = rev_mod.get('total')

    if prod_id and store_id and revs_cnt and int(revs_cnt) > 0:
        revs_url = 'https://media.flixcar.com/modular/get-reviews/es/731/{prod_id}/?prodId={prod_id}&iso=es&distId=731&id={store_id}&page_opt=1&sort_opt=rating_high&lang_opt=&star_opt=&per_page_opt=10'.format(prod_id=prod_id, store_id=store_id)
        session.do(Request(revs_url, force_charset='utf-8'), process_reviews, dict(context, prod_id=prod_id, store_id=store_id, revs_cnt=int(revs_cnt)))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    try:
        revs = simplejson.loads(data.content).get('data', [])
    except:
        revs = []

    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('submission_time')
        if date:
            review.date = date.replace('/', '-')

        author = rev.get('review_each_username')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        best = rev.get('rating_range') or 5.0
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=float(best)))

        if rev.get('IsRecommended'):
            review.add_property(type='is_recommended', value=True)

        title = rev.get('review_each_title')
        excerpt = rev.get('description')
        if excerpt:
            review.title = title
        elif title:
            excerpt = title

        if excerpt and len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    offset = context.get('offset', 0) + 10
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        next_url = 'https://media.flixcar.com/modular/get-reviews/es/731/{prod_id}/?prodId={prod_id}&iso=es&distId=731&id={store_id}&page_opt={page}&sort_opt=rating_high&lang_opt=&star_opt=&per_page_opt=10'.format(prod_id=context['prod_id'], store_id=context['store_id'], page=next_page)
        session.do(Request(next_url, force_charset='utf-8'), process_reviews, dict(context, product=product, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
