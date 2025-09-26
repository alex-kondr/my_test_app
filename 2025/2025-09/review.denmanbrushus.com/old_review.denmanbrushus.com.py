from agent import *
from models.products import *
import simplejson


XCAT = ['Shop all', 'Choose your hair goal']


def run(context, session):
    session.queue(Request("https://denmanbrushus.com/", force_charset="utf-8"), process_frontpage, dict(cat='Hairbrushes'))


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@class="mega-menu__list"]/li/div/a')
    for cat in cats:
        url = cat.xpath('@href').string()
        name = cat.xpath('text()').string()
        if name not in XCAT:
            session.queue(Request(url, force_charset="utf-8"), process_prods_json, dict(cat=context['cat'] + '|' + name))


def process_prods_json(data, context, session):
    prods_json = data.xpath('''//script[contains(., '"collection_viewed", ')]//text()''').string()
    if not prods_json:
        return

    prods_json = prods_json.split('"collection_viewed", ')[-1].split(');},')[0]
    prods_json = simplejson.loads(prods_json)

    prods = prods_json.get('collection', {}).get('productVariants', [])
    for prod in prods:
        name = prod.get('product', {}).get('title')
        url = 'https://denmanbrushus.com' + prod.get('product', {}).get('url', '')
        ssid = prod.get('id')
        session.queue(Request(url, force_charset="utf-8"), process_product, dict(context, name=name, url=url, ssid=ssid))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.ssid = context['ssid']
    product.manufacturer = 'Denman'

    try:
        prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type": "Product"')]//text()''').string())

        mpn = prod_json.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('offers', [{}])[0].get('gtin12')
        if ean:
            product.add_property(type='id.ean', value=ean)
    except:
        pass

    pid = data.xpath('//div[@class="ruk_rating_snippet"]/@data-sku').string()

    if pid:
        revs_url = 'https://api.reviews.co.uk/product/review?store=www.denmanbrush.com&sku=' + pid + '&mpn=&lookup=&product_group=&minRating=1&tag=&sort=undefined&per_page=10&page=1'
        session.do(Request(revs_url, force_charset='utf-8'), process_reviews, dict(product=product, pid=pid))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('reviews', {}).get('data', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev['product_review_id'])
        review.title = rev.get('title')

        date = rev.get('date_created')
        if date:
            review.date = date.split()[0]

        first_name = rev.get('reviewer', {}).get('first_name') or ''
        last_name = rev.get('reviewer', {}).get('last_name') or ''
        author = first_name + ' ' + last_name
        if author.strip():
            author = author.strip()
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.get('reviewer', {}).get('verified_buyer')
        if is_verified and is_verified == "yes":
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.get('review')
        if excerpt:

            excerpt = excerpt.encode("ascii", errors="ignore").strip()

            if excerpt:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = context.get('revs_cnt', revs_json.get('stats', {}).get('count'))
    offset = context.get('offset', 0) + 10
    if revs_cnt and int(revs_cnt) > offset:
        next_page = context.get('page', 1) + 1
        next_url = 'https://api.reviews.co.uk/product/review?store=www.denmanbrush.com&sku=' + context['pid'] + '&mpn=&lookup=&product_group=&minRating=1&tag=&sort=undefined&per_page=10&page=' + str(next_page)
        session.do(Request(next_url, force_charset='utf-8'), process_reviews, dict(context, product=product, revs_cnt=revs_cnt, offset=offset, page=next_page))
    elif product.reviews:
        session.emit(product)
