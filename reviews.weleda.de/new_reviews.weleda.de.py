from agent import *
from models.products import *
import simplejson


XCAT = ['Angebote', 'Weleda', 'Magazin']


def run(context, session):
    session.queue(Request('https://www.weleda.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[button[contains(@aria-controls, "sub-menu-")]]')
    for cat in cats:
        name = cat.xpath('a[@class="megamenu-item"]/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('.//li[@itemprop="name"]/a[@class="megamenu-item"]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('.//text()').string(multiple=True)

                if 'Alle' not in sub_name:
                    cat_id = sub_cat.xpath('@href').string().split('-')[-1]
                    url = 'https://www.weleda.de/restapi/search/products-for-category?categoryId={cat_id}'.format(cat_id=cat_id)
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name, cat_id=cat_id))


def process_prodlist(data, context, session):
    prods_json = simplejson.loads(data.content)

    prods = prods_json.get('productTeaserData', {}).get('productTeasers', [])
    for prod in prods:
        name = prod.get('name')
        sku = prod.get('globalId')
        url = prod.get('productUrl')

        revs_cnt = prod.get('rating', {}).get('reviewCount')
        if revs_cnt and revs_cnt > 0:
            session.queue(Request(url), process_product, dict(context, name=name, sku=sku, url=url))

    next_page = context.get('page', 1) + 1
    pages_cnt = prods_json.get('productTeaserData', {}).get('paginationResponseData', {}).get('maxPage')
    if next_page <= pages_cnt:
        url = 'https://www.weleda.de/restapi/search/products-for-category?categoryId={cat_id}'.format(cat_id=context['cat_id'])
        session.queue(Request(url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('-' + context['sku'], '')
    product.category = context['cat']
    product.sku = context['sku']

    prod_json = data.xpath('//div[@class="wl-content-wrapper tint-chlorophyll"]/@ng-init').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json.replace('this.product = ', '').replace('; this.init();', ''))

        ean = prod_json.get('variants', [{}])[0].get('ean')
        if ean:
            product.add_property(type='id.ean', value=ean)

    revs_url = 'https://www.weleda.de/restapi/review/abstract-product?sku={sku}&ipp=9999'.format(sku=context['sku'])
    session.queue(Request(revs_url), process_reviews, dict(context, product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    revs = revs_json.get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        author = rev.get('author')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        is_verified_buyer = rev.get('verified')
        if is_verified_buyer:
            review.add_property(type="is_verified_buyer", value=True)

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.get('summary')
        excerpt = rev.get('description')
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            ssid = rev.get('id')
            if ssid:
                review.ssid = str(ssid)
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
