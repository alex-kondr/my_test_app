from agent import *
from models.products import *
import simplejson


XCAT = ['Clearance', 'Brands', 'Hot Deals']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.smarthomesounds.co.uk/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//a[regexp:test(@class, "^level-0")]')
    for cat in cats:
        name = cat.xpath('.//text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    cats = data.xpath('//a[@class="group hover:underline"]')
    for cat in cats:
        name = cat.xpath('img/@title').string()
        url = cat.xpath('@href').string()

        if ' all ' not in name.lower() and 'offers' not in name.lower() and 'deals' not in name.lower():
            session.queue(Request(url), process_prodlist, dict(cat=context['cat'] + '|' + name))


def process_prodlist(data, context, session):
    prods = data.xpath('//link[@rel="next"]/@href')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()

        if name and url:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]

    sku = data.xpath('//div[@class="product_ruk_rating_snippet"]/@data-sku').string()
    if sku:
        product.sku = sku

        revs_type = data.xpath('//a[contains(., "Reviews")]/@href').string().split('/')[-1]
        revs_url = 'https://api.reviews.co.uk/timeline/data?store={revs_type}&page=1&per_page=150&sku={sku}'.format(revs_type=revs_type, sku=sku)
        session.do(Resuest(revs_url, force_charset='utf-8'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.context)

    revs = revs_json.get('timeline', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        ssid = rev.get('_source', {}).get('_id')
        if ssid:
            review.ssid = ssid.split('-')[-1]
        else:
            review.ssid = review.digest() if author else review.digest(excerpt)

        date = rev.get('_source', {}).get('date_created')
        if date:
            review.date = date.split()[0]

        author = rev.get('_source', {}).get('author')
        author_ssid = rev.get('_source', {}).get('user_id')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=author_ssid))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('_source', {}).get('rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.get('_source', {}).get('helpful')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        title = rev.get('_source', {}).get('review_title')
        excerpt = rev.get('_source', {}).get('comments')
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.strip(' \n\r.+-')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

            ssid = rev.get('_source', {}).get('_id')
            if ssid:
                review.ssid = ssid.split('-')[-1]
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(excerpt)

    revs_cnt = rev.get('stats', {}).get('review_count', 0)
    next_page = context.get('page', 1) + 1
    offset = context.get('offset', 0) + 150
    if offset < int(revs_cnt):
        next_url = data.response_url.replace('&page='+str(next_page-1), '&page='+str(next_page))
        session.do(Request(next_url, force_charset='utf-8'), process_reviews, dict(product=product, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
