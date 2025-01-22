from agent import *
from models.products import *
import simplejson
import datetime
import re


CLEANR = re.compile('<.*?>')


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request("https://onikumagaming.com/collections/all-products?page=1", use="curl"), process_prodlist, dict())


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath("//a[@data-action='wk-add']")
    for prod in prods:
        url = prod.xpath("@href").string()
        session.queue(Request(url), process_product, dict(context, url=url))

    next_url = data.xpath("//link[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    json = data.xpath("//script[contains(.,'window.ShopifyAnalytics = window.ShopifyAnalytics')]/text()").string()
    json = json.split(";")[3].split(" = ")[-1].strip(";")
    json = simplejson.loads(json)

    product = Product()

    name = data.xpath("//h1[@itemprop='name']/text()").string()
    if not name:
        name = data.xpath("//h3[@data-product-type='title']/text()").string()
    product.name = name

    product.url = context["url"]
    product.sku = json["product"]["variants"][0]["sku"]
    product.ssid = product.sku
    product.category = json["product"]["type"]
    product.manufacturer = "ONIKUMA"
    product_id = json["product"]["id"]

    session.do(Request("https://reviews.atomee.com/apr/getReviews", method="POST", data={
        "shop_id": 11212030016,
        "product_id": product_id,
        "sorted_by": "most_recent",
        "request_page": 1,
        "filter": 1}),
        process_revs, dict(context, product=product, product_id=product_id, request_page=1)
    )

    if product.reviews:
        session.emit(product)


def process_revs(data, context, session):
    product = context["product"]

    revs = simplejson.loads(data.getcontent())["reviews"]
    if not revs:
        return

    for rev in revs:
        review = Review()
        review.type = "user"
        review.date = datetime.datetime.fromtimestamp(rev["date"]).strftime("%Y-%m-%d")
        review.url = product.url

        review.grades.append(Grade(type="overall", value=rev["review_star_rating"], best=5))

        author_name = rev["name"].encode("ascii", errors="ignore")
        review.authors.append(Person(name=author_name, ssid=author_name))

        is_verified = rev["verified"]
        review.add_property(type='is_verified_buyer', value=is_verified)

        excerpt = re.sub(CLEANR, '', rev["content"])
        excerpt = excerpt.encode("ascii", errors="ignore").replace("\r", " ")
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest() if author_name else review.digest(excerpt)
            product.reviews.append(review)

    context["request_page"] += 1
    session.do(Request("https://reviews.atomee.com/apr/getReviews", method="POST", data={
        "shop_id": 11212030016,
        "product_id": context["product_id"],
        "sorted_by": "most_recent",
        "request_page": context["request_page"], "filter": 1}),
        process_revs, dict(context, product=product)
    )
