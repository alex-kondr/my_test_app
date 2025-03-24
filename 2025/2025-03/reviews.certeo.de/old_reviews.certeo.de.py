from agent import *
from models.products import *
import simplejson
import httplib


httplib._MAXHEADERS = 500


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.kaiserkraft.de/', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats1 = data.xpath('//ul[@data-test-id="top-categories-id"]/li')
    for cat1 in cats1:
        name1 = cat1.xpath('span/text()').string()
        cats2 = cat1.xpath('div/ul/li')
        for cat2 in cats2:
            name2 = cat2.xpath('a/span/text()').string()
            cats3 = cat2.xpath('div/ul/li[@data-test-id="subcategory-id"]/a')
            for cat3 in cats3:
                name3 = cat3.xpath('.//text()').string()
                url = cat3.xpath('@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name1+'|'+name2))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@data-test-id="product-grid-item"]')
    for prod in prods:
        name = prod.xpath('.//div[@data-test-id="product-name"]/span/text()').string()
        url = prod.xpath('a/@href').string()
        ssid = prod.xpath('div/@data-impression-product').string()

        revs_cnt = prod.xpath('.//div/@data-rating-count').string()
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url, ssid=ssid))

    next_url = data.xpath('//a[contains(@data-test-id, "pagination-next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.ssid = context['ssid']

    sku = data.xpath('//div[@data-test-id="pdp-article-number"]/text()').string()
    if sku:
        if '(' in sku:
            mpn = sku.split('(')[-1].strip(' )')
            if len(mpn) > 4:
                product.properties.append(ProductProperty(type='id.manufacturer', value=mpn))

        product.sku = sku.split(':')[-1].split('(')[0].strip()

    manufacturer = data.xpath('''//script[contains(., '"brandLogoUrl"')]/text()''').string()
    if manufacturer:
        product.manufacturer = manufacturer.split('brandLogoUrl":')[-1].split('altText":"', 1)[-1].split('",')[0]

    options = '-H "x-requested-by: scale-frontend" --compressed'
    revs_url = 'https://www.kaiserkraft.de/api/shops/www.kaiserkraft.de/products/{}/reviews?lang=de&page=1&reviewsPerPage=10000'.format(product.ssid)
    session.do(Request(revs_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    revs = revs_json.get('reviews', [])
    for rev in revs:
        if rev.get('lang') != 'de':
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('id')

        date = rev.get('date')
        if date:
            review.date = date.split('T')[0]

        # No author

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        excerpt = rev.get('comment')
        if excerpt:
            excerpt = excerpt.replace('\r', '').replace('\n', ' ').replace('<br />', ' ').strip()
            review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # No next page
