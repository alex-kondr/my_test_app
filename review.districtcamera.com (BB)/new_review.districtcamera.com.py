from agent import *
from models.products import *
import simplejson
import HTMLParser


h = HTMLParser.HTMLParser()


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.districtcamera.com/', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@class="mobile-menu__nav"]')
    for cat in cats:
        name = cat.xpath('.//a[contains(@class, "text--strong")]/text()').string()

        if name:
            sub_cats = cat.xpath('.//a[@data-type]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string()
                session.queue(Request(url, force_charset='utf-8', max_age=0), process_catlist, dict(cat=name + '|' + sub_name))


def process_catlist(data, context, session):
    sub_cats = data.xpath('//a[@class="collection-item"]')
    for sub_cat in sub_cats:
        sub_name = sub_cat.xpath('following-sibling::div[1]//img/@alt').string()
        url = sub_cat.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8', max_age=0), process_prodlist, dict(cat=context['cat'] + '|' + sub_name))

    process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    prods = data.xpath('//a[contains(@class, "product-item__title")]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat']

    manufacturer = data.xpath('//div[@class="collection-logo"]/a/@href').string()
    if manufacturer:
        product.manufacturer = manufacturer.split('/')[-1].title()

    mpn = data.xpath('//span[span[contains(., "MPN:")]]/text()[normalize-space(.)]').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//span[@class="product-meta__sku-number"]/text()').string()
    if ean and ean.isdigit() and len(ean) > 11:
        product.add_property(type='id.ean', value=ean)

    url = 'https://www.shopperapproved.com/product/15521/' + ean + '.js'
    session.do(Request(url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    if 'tempreviews' not in data.content:
        return

    revs_json = data.content.replace("\n", "").split("var tempreviews = ")[-1].split(";sa_product_reviews")[0].split(";sa_merchant_reviews")[0]

    revs = simplejson.loads(revs_json)
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev['id']
        review.date = rev.get('date')

        author = rev.get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_recommended = rev.get('recommend')
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        is_verified = rev.get('verified')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('heading')
        excerpt = rev.get('comments')
        if excerpt and len(h.unescape(excerpt)) > 3:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = h.unescape(excerpt).replace('<br>', ' ').strip()
            if len(excerpt) > 3:

                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
