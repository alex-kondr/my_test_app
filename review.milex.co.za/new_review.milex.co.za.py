from agent import *
from models.products import *

import simplejson


XCAT = ["View the Milex Range", "Request Spares"]


def run(context, session):
    session.queue(Request("https://milex.co.za/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath("//li[contains(@class, 'lvl1 parent dropdown')]")
    for cat in cats:
        name = cat.xpath("a/text()").string()

        sub_cats = cat.xpath(".//li")
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath("a/text()").string()
            url = sub_cat.xpath("a/@href").string()

            if sub_name not in XCAT:
                session.queue(Request(url), process_prodlist, dict(cat=name + "|" + sub_name, url=url))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[contains(@class, 'grid grid--uniform grid-products grid--view-items')]/div")
    for prod in prods:
        name = prod.xpath(".//a[contains(@class, 'grid-view-item__title')]/text()").string()
        url = prod.xpath(".//a[contains(@class, 'grid-view-item__title')]/@href").string()

        revs = prod.xpath(".//span[contains(@class, 'jdgm-prev-badge__text')]/text()").string()
        if url and revs != "No reviews":
            session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product_json = data.xpath("""//script[@type='application/ld+json']/text()[contains(., '"@type": "Product"')]""").string()
    product_json = simplejson.loads(product_json)

    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = data.xpath("//input[@name='product-id']/@value").string()
    product.category = context["cat"]
    product.manufacturer = "Milex"
    product.sku = product_json["sku"]
    product.add_property(type='id.manufacturer', value=product_json["mpn"])

    revs_url = "https://judge.me/reviews/reviews_for_widget?url=milex-south-africa.myshopify.com&shop_domain=milex-south-africa.myshopify.com&platform=shopify&page="
    session.do(Request(revs_url + '1' + "&per_page=5&product_id=" + product.ssid), process_reviews, dict(product=product, revs_url=revs_url))


def process_reviews(data, context, session):
    product = context["product"]

    revs_json = simplejson.loads(data.content.replace("{}\r\n", ''))
    new_data = data.parse_fragment(revs_json["html"])

    revs = new_data.xpath("//div[@class='jdgm-rev-widg__reviews']/div")
    for rev in revs:
        review = Review()
        review.type = "user"
        review.title = rev.xpath(".//b[@class='jdgm-rev__title']/text()").string()
        review.ssid = rev.xpath("@data-review-id").string()
        review.url = product.url

        date = rev.xpath(".//span[contains(@class, 'jdgm-rev__timestamp')]/@data-content").string()
        if date:
            review.date = date.split(' ')[0]

        is_verified_buyer = rev.xpath("@data-verified-buyer").string()
        if is_verified_buyer == "true":
            review.add_property(type="is_verified_buyer", value=True)

        grade_overall = rev.xpath(".//span[contains(@class, 'jdgm-rev__rating')]/@data-score").string()
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        author_name = rev.xpath(".//span[@class='jdgm-rev__author']/text()").string()
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        excerpt = rev.xpath(".//div[@class='jdgm-rev__body']//text()").string(multiple=True)
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)

    if revs:
        page = context.get("page", 1) + 1
        session.do(Request(context["revs_url"] + str(page) + "&per_page=5&product_id=" + product.ssid), process_reviews, dict(context, product=product, page=page))

    elif product.reviews:
        session.emit(product)
