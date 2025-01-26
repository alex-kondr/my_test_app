from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://onikumagaming.com/collections/all-products?view=all'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//h2[@class="tt-title prod-thumb-title-color"]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = 'Tech'

    prod_info = data.xpath('//script[contains(., "Viewed Product")]/text()').string()
    if prod_info:
        prod_info = simplejson.loads(prod_info.split('.track("Viewed Product",')[-1].split(',undefined,undefined')[0])

        product.category = prod_info.get('category')
        product.manufacturer = prod_info.get('brand')

        mpn = prod_info.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//input[@name="product-id"]/@value').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[@data-pf-type="Row" and .//h3[contains(., "WHAT PEOPLE SAY")]]/following-sibling::div[@data-pf-type="Row"]/div')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        author = rev.xpath('.//span[@data-pf-type="Text"]/text()[contains(., "--")]').string()
        if author:
            author = author.strip(' +-.')
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//i[contains(@class, "pfa-star")])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.xpath('.//div/@title').string()
        excerpt = rev.xpath('.//span[@data-pf-type="Text"]/text()[not(contains(., "--"))]').string()
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.strip(' +-.')
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
