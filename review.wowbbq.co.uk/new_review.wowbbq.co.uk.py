from agent import *
from models.products import *
import simplejson


XCAT = ['Clearance', 'View All']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.wowbbq.co.uk/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "nav-item level0")]')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        if name not in XCAT:
            sub_cats = cat.xpath('.//div[contains(@class, "nav-item level1")]')

            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a//text()').string(multiple=True)

                if 'All ' not in sub_name:
                    sub_cats1 = sub_cat.xpath('.//div[contains(@class, "nav-item level2")]/a')

                    if sub_cats1:
                        for sub_cat1 in sub_cats1:
                            sub_name1 = sub_cat1.xpath('span//text()').string()
                            url = sub_cat1.xpath('@href').string()

                            if 'All ' not in sub_name1:
                                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))

                    else:
                        url = sub_cat.xpath('a/@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//a[@class="product-item-link"]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.sku = data.xpath('//form/@data-product-sku').string()
    product.ssid = data.xpath('//form[@data-product-sku="{}"]//input[@name="product"]/@value'.format(product.sku)).string()
    product.manufacturer = 'Weber'

    ean = data.xpath('//span[contains(., "Barcode")]/text()[contains(., "Barcode:")]').string(multiple=True)
    if ean:
        ean = ean.split()[-1]
        if ean and ean.isdigit():
            product.add_property(type='id.ean', value=ean)

    if product.sku:
        revs_url = "https://api.reviews.co.uk/timeline/data?type=product_review&store=wowbbq&sort=date_desc&page=1&per_page=10&sku=" + product.sku + "&lang=en&enable_avatars=true&include_subrating_breakdown=1"
        session.do(Request(revs_url, force_charset='utf-8'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('timeline', [])
    for rev in revs:
        rev = rev.get('_source', {})

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('_id', '').split('-')[-1]

        date = rev.get('date_created')
        if date:
            review.date = date.split()[0]

        author = rev.get('author')
        author_ssid = rev.get('author_id')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=author_ssid))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.get('order_id')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('helpful')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        is_recommended = rev.get('would_recommend_product')
        if is_recommended:
            review.add_property(value=True, type='is_recommended')

        title = rev.get('review_title')
        excerpt = rev.get('comments')
        if excerpt and len(excerpt.strip()) > 2:
            if title:
                review.title = title.strip()
        else:
            review.title = excerpt

        if excerpt:
            excerpt = excerpt.strip()
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    revs_cnt = revs_json.get('stats', {}).get('review_count')
    offset = context.get('offset', 0) + 10
    if revs_cnt and int(revs_cnt) > offset:
        next_page = context.get('page', 1) + 1
        next_url = "https://api.reviews.co.uk/timeline/data?type=product_review&store=wowbbq&sort=date_desc&page=" + str(next_page) + "&per_page=10&sku=" + product.sku + "&lang=en&enable_avatars=true&include_subrating_breakdown=1"
        session.do(Request(next_url, force_charset='utf-8'), process_reviews, dict(product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
