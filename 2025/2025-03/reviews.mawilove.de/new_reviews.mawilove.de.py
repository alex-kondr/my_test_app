from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.mawilove.de/de/shop/'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-card-base"]')
    for prod in prods:
        name = prod.xpath('h2[contains(@class, "title")]//text()').string(multiple=True)
        url = prod.xpath('a/@href').string()

        rating = prod.xpath('.//strong[@class="rating"]/text()').string()
        if rating and float(rating) > 0:
            session.queue(Request(url), process_product, dict(name=name, url=url))

# no next page


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = "Beauty"
    product.manufacturer = "MawiLove"

    prod_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)
        product.sku = str(prod_json.get('sku'))

    revs = data.xpath('//div[@class="comment_container"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@id').string().replace('comment-', '')

        # no date

        author = rev.xpath('.//strong[contains(@class, "author")]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//strong[@class="rating"]/text()').string()
        if grade_overall:
            review.grades.append(Grade(type='grade.overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.xpath('.//em[contains(@class, "verified")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.xpath('.//div[@class="description"]/p//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
