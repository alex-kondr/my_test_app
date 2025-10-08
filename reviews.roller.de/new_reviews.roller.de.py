from agent import *
from models.products import *
import simplejson


XCAT = ['Wohnideen', 'SALE', 'Marken', 'Prospekte', 'Gutscheine', 'Wohnbereiche', 'Küchenstudio', 'Planung und Beratung']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request('https://www.roller.de/', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//a[@aria-label="Kategorie"]')
    for cat in cats:
        name = cat.xpath('span/text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, max_age=0), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    cats = data.xpath('//a[@data-id="main-category-card" or @data-v-76982744="data-v-76982744"]')
    for cat in cats:
        name = cat.xpath('span/@customarialabel').string().replace('Kategorie ', '')
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, max_age=0), process_catlist, dict(cat=context['cat'] + '|' + name))

    if not cats:
        category = data.response_url.split('/')[-2]
        url = 'https://www.roller.de/nuxt-api/view/category/{}/products?page=0&q=:relevance:averageCustomerRating:Ein%2BStern%2Bund%2Bmehr&sort=relevance'.format(category)
        session.queue(Request(url, force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_prodlist(data, context, session):
    prods_json = simplejson.loads(data.content)

    prods = prods_json.get('products', [])
    for prod in prods:
        name = prod.get('name')
        ssid = prod.get('code')
        manufacturer = prod.get('brandName')
        prod_url = 'https://www.roller.de' + prod.get('url')

        revs_cnt = prod.get('rating', {}).get('count')
        if revs_cnt and int(revs_cnt) > 0:
            url = 'https://www.roller.de/nuxt-api/view/products/{}/reviews?page=0&sort=rating&rating'.format(ssid)
            session.do(Request(url, max_age=0), process_reviews, dict(context, name=name, ssid=ssid, manufacturer=manufacturer, prod_url=prod_url))

    curr_page = prods_json.get('pagination', {}).get('currentPage', 0)
    total_pages = prods_json.get('pagination', {}).get('totalPages', 0)
    if curr_page < total_pages:
        next_url = data.response_url.replace('page='+str(curr_page), 'page='+str(curr_page+1))
        session.queue(Request(next_url, force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_reviews(data, context, session):
    product = context.get('product')
    if not product:
        product = Product()
        product.name = context['name']
        product.url = context['prod_url']
        product.ssid = context['ssid']
        product.sku = product.ssid
        product.category = context['cat']
        product.manufacturer = context['manufacturer']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('comments', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        date = rev.get('date')
        if date:
            review.date = date.split('T')[0]

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        # no author

        excerpt = rev.get('comment')
        if excerpt:
            excerpt = excerpt.replace('\n', '').strip(' +-."*')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = revs_json.get('count')
    offset = context.get('offset', 0) + 8
    if offset < revs_cnt:
        next_page = context.get('page', 0) + 1
        next_url = 'https://www.roller.de/nuxt-api/view/products/{ssid}/reviews?page={page}&sort=rating&rating'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url, max_age=0), process_reviews, dict(product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
