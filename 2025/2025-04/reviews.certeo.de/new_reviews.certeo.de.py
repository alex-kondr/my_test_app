from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.kaiserkraft.de/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@data-test-id="top-categories-id"]/li')
    for cat in cats:
        name = cat.xpath('span/text()').string()

        sub_cats = cat.xpath('div/ul/li')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('a/span/text()').string()

            sub_cats1 = sub_cat.xpath('div/ul/li[@data-test-id="subcategory-id"]/a')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('.//text()').string(multiple=True)
                url = sub_cat1.xpath('@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@data-test-id="product-grid-item"]')
    for prod in prods:
        name = prod.xpath('.//div[@data-test-id="product-name"]/span/text()').string()
        url = prod.xpath('a/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(@data-test-id, "pagination-next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.sku = product.ssid
    product.category = context['cat']

    manufacturer = data.xpath('''//script[contains(., '"brandLogoUrl"')]/text()''').string()
    if manufacturer:
        product.manufacturer = manufacturer.split('brandLogoUrl":')[-1].split('altText":"', 1)[-1].split('",')[0]

    mpn = data.xpath('//div[@data-test-id="pdp-article-number"]/text()').string()
    if mpn:
        mpn = mpn.split(':')[-1].strip()
        product.add_property(type='id.manufacturer', value=mpn)

    revs_cnt = data.xpath('//span[@data-test-id="rating-id"]//span[not(@class)]/text()').string()
    if revs_cnt and int(revs_cnt.strip('()')) > 0:
        options = '-H "x-requested-by: scale-frontend" --compressed'
        revs_url = 'https://www.kaiserkraft.de/api/shops/www.kaiserkraft.de/products/{}/reviews?lang=de&page=1&reviewsPerPage=10'.format(product.ssid)
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

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        excerpt = rev.get('comment')
        if excerpt:
            excerpt = excerpt.replace('\r', '').replace('\n', ' ').replace('<br />', ' ').strip(' +-.')
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                product.reviews.append(review)

    revs_cnt = revs_json.get('numberOfReviews')
    offset = context.get('offset', 0) + 10
    if offset < int(revs_cnt):
        next_page = context.get('page', 1) + 1
        options = '-H "x-requested-by: scale-frontend" --compressed'
        revs_url = 'https://www.kaiserkraft.de/api/shops/www.kaiserkraft.de/products/{ssid}/reviews?lang=de&page={page}&reviewsPerPage=10'.format(ssid=product.ssid, page=next_page)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
