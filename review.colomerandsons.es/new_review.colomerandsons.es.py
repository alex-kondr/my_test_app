from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://colomerandsons.com/categoria-producto/relojes/'), process_prodlist, dict(cat='Relojes'))


def process_prodlist(data, context, session):
    prods = data.xpath('//ul/li[contains(@class, "type-product")]')
    for prod in prods:
        name = prod.xpath('.//h3[contains(@class, "product_title")]//a/text()').string()
        url = prod.xpath('.//h3[contains(@class, "product_title")]//a/@href').string()

        rating = prod.xpath('.//strong[@class="rating"]')
        if rating:
            session.queue(Request(url+'?clang=es'), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@class="product_id" or @name="product_id"]/@value').string()
    product.category = context['cat']

    prod_json = data.xpath("""//script[contains(., '"@type":"Product"')]/text()""").string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        mpn = prod_json.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

    revs = data.xpath('//ol[@class="commentlist"]/li/div')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//time/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//p/strong[contains(@class, "review__author")]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span/strong[@class="rating"]/text()').string()
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//p/em[contains(@class, "verified")]')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.xpath('.//div[@class="description"]/p/text()').string(multiple=True)
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            ssid = rev.xpath('@id').string()
            if ssid:
                review.ssid = ssid.split('-')[-1]
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # Loaded all revs
