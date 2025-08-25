from agent import *
from models.products import *
import simplejson


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.mawilove.de/collections/produkte', use='curl', force_charset='utf-8'), process_prodlist, dict())


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//div[@class="card__content" and .//div[@data-number-of-reviews]]')
    for prod in prods:
        name = prod.xpath('.//h3//text()').string(multiple=True)
        url = prod.xpath('.//h3/a/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict())


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="id"]/@value').string() or product.url.split('/')[-1]
    product.sku = data.xpath('//input[@name="product-id"]/@value').string()
    product.category = "Beauty"
    product.manufacturer = "MawiLove"

    prod_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        ean = prod_json.get('gtin')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[contains(@class, "desktop-review")]//div[contains(@class, "item")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        author = rev.xpath('.//div[@class="testimonial-text"]/p[last()]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        excerpt = rev.xpath('.//div[@class="testimonial-text"]/p//text()').string(multiple=True)
        if excerpt:
            excerpt = excerpt.replace(author, '').strip()
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
