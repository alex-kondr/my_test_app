from agent import *
from models.products import *
import simplejson


XCAT = ["Nursery Sets", "Kids' Bedroom Sets", 'Shop by Character']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.deltachildren.com/'), process_frontpage, dict())
    session.queue(Request('https://www.deltachildren.com/collections/wagons'), process_prodlist, dict(cat='Wagons'))


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[li[contains(@class, "site-header__nav-item--bottom")]]')
    for cat in cats:
        name = cat.xpath('(li[contains(@class, "site-header__nav-item--bottom")]/a)[last()]/text()').string()

        sub_cats = cat.xpath('li[contains(@class, "site-header__nav-subitem--mega")]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string(multiple=True)
            url = sub_cat.xpath('a/@href').string()

            if sub_name not in XCAT:
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//a[@class="product__title product__item-title"]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

# no next page


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div/@data-id').string()
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = 'Delta Children'

    mpn = data.xpath('//span[@id="display_sku"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//span[@id="display_upc"]/text()').string()
    if ean and ean.isdigit() and len(ean) > 11:
        product.add_property(type='id.ean', value=ean)

    revs_cnt = data.xpath('//span[@class="jdgm-prev-badge__text"]/text()').string()
    if revs_cnt and revs_cnt.replace('reviews', '').strip().isdigit() and int(revs_cnt.replace('reviews', '')) > 0:
        revs_url = 'https://delta-children.vercel.app/reviews/single?id=' + product.ssid
        session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = simplejson.loads(data.content).get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('reviewer', {}).get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.get('title')
        excerpt = rev.get('body')
        if excerpt and len(excerpt) > 1:
            review.title = title
        else:
            excerpt = title

        if excerpt and len(excerpt) > 1:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
