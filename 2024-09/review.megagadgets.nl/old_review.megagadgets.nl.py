from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request("https://www.megagadgets.nl/alles.html?product_list_dir=desc&product_list_limit=108&product_list_order=reviews_count", force_charset="utf-8"), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-card__details")][.//div[@class="reviews-actions"]]/a')
    for prod in prods:
        name = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url, force_charset="utf-8"), process_product, dict(name=name, url=url))

    next_url = data.xpath("//link[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url, force_charset="utf-8"), process_prodlist, dict())


def process_product(data, context, session):
    prod_json = simplejson.loads(data.xpath('''//script[@type="application/ld+json"][contains(., '"@type":"Product"')]//text()''').string())

    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.manufacturer = prod_json.get('manufacturer')
    product.ssid = data.xpath('//div[@class="product-summary__form"]//input[@name="product"]/@value').string()
    product.sku = prod_json.get('sku')

    category = ''
    cats = data.xpath('//li[contains(@class, "category")]/a/@title')
    for cat in cats:
        category += cat.string() + '|'
    if category:
        product.category = category.strip('|')

    ean = prod_json.get('gtin13')
    if ean:
        product.add_property(type="id.ean", value=ean)

    revs = prod_json.get('review', [])
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url

        date = rev.get('datePublished')
        if date:
            review.date = date.split()[0]

        author = rev.get('author', {}).get('name')
        if author:
            email = rev.get('name')
            if email and "@" in email:
                review.authors.append(Person(name=author, ssid=author, email=email))
            else:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('reviewRating', {}).get('ratingValue')
        if grade_overall:
            value = float(grade_overall / 20)
            review.grades.append(Grade(type="overall", value=value, best=5.0))

        excerpt = rev.get('description')
        if excerpt:
            excerpt = excerpt.split("---")[0].replace('\r\n', ' ')

            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # no next page, no more than 22 revs
