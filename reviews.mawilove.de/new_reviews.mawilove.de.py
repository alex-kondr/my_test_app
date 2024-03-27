from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.mawilove.de/de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@id="menu-item-6974"]/ul[@class="sub-menu"]//a')
    if cats:
        for cat in cats[::-1]:
            name = cat.xpath('text()').string()
            url = cat.xpath('@href').string()
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-card-base"]')
    for prod in prods:
        name = prod.xpath('.//h2[@class="woocommerce-loop-product__title"]//text()').string(multiple=True)
        url = prod.xpath('a[contains(@class, "woocommerce")]/@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    revs_cnt = data.xpath('//span[contains(., "Bewertungen")]/text()').string()
    if not revs_cnt or int(revs_cnt.replace('Bewertungen', '')) < 1:
        return

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']

    prod_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('@graph', [{}])[0].get('manufacturer', {}).get('name')

        ean = prod_json.get('@graph', [{}])[0].get('gtin13')
        if ean and ean.isdigit() and len(ean) > 12:
            product.add_property(type='id.ean', value=ean)

    context['product'] = product

    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//li[contains(@class, "review")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//time/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//strong[@class="woocommerce-review__author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span/@style').string()
        if grade_overall:
            grade_overall = float(grade_overall.replace('width:', '').replace('%', '')) / 20
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//div[@class="description"]/p//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
