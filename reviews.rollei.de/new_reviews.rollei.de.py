from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.rollei.de/collections/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//a[contains(@class, "card-link")]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=name))

    next_url = data.xpath('//a[contains(., "Nächste")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_catlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//li[product-card]')
    for prod in prods:
        name = prod.xpath('.//a[contains(@class, "card-link")]/text()').string()
        url = prod.xpath('.//a[contains(@class, "card-link")]/@href').string()

        revs_cnt = prod.xpath('.//div/@data-rating-count').string()
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]
    product.sku = product.sku
    product.category = context['cat']

    prod_info_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if prod_info_json:
        prod_info_json = simplejson.loads(prod_info_json)

        manufacturer = prod_info_json.get('name')
        if manufacturer:
            product.manufacturer = manufacturer.strip()

    ean = data.xpath('//span/@data-barcode').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    mpn = data.xpath('//input[@name="product-id"]/@value').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

        revs_url = 'https://cdn.fera.ai/api/v3/public/products/{mpn}/reviews.json?client=fjs-3.3.6&api_key=pk_7f2fd279edefe8b4c08623df6c92c01b6dfa1996ea6fac42a2b22945361b8faa&page_size=6&sort_by=quality%3Adesc&include_aggregate_rating=true&offset=0&limit=6&include_product=true'.format(mpn=mpn)
        session.do(Request(revs_url), process_reviews, dict(product=product, mpn=mpn))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('data', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('id')

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('customer', {}).get('id')
        author_ssid = rev.get('customer', {}).get('display_name')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=author_ssid))

        grade_overall = rev.get('rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('is_verified')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('heading')
        excerpt = rev.get('body')
        if excerpt and len(excerpt) > 1:
            if title:
                review.title = title.replace('&amp;', '&')
        else:
            excerpt = title

        if excerpt and len(excerpt) > 1:
            excerpt = excerpt.replace('&amp;', '&')
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    revs_cnt = revs_json.get('meta', {}).get('total_count', 0)
    offset = context.get('offset', 0) + 6
    if offset < revs_cnt:
        next_url = 'https://cdn.fera.ai/api/v3/public/products/{mpn}/reviews.json?client=fjs-3.3.6&api_key=pk_7f2fd279edefe8b4c08623df6c92c01b6dfa1996ea6fac42a2b22945361b8faa&page_size=6&sort_by=quality%3Adesc&include_aggregate_rating=true&offset={offset}&limit=6&include_product=true'.format(mpn=context['mpn'], offset=offset)
        session.do(Request(next_url), process_reviews, dict(context, product=product, offset=offset))

    elif product.reviews:
        session.emit(product)
