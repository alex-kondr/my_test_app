from agent import *
from models.products import *

import simplejson


def run(context, session):
    session.queue(Request('https://www.wowbbq.co.uk/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath("//li[contains(@class,'li-level-1')]")
    for cat in cats:
        name = cat.xpath("a/text()").string()

        sub_cats = cat.xpath(".//li[contains(@class,'li-level-2')]")
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath("a/text()").string()

            sub_cats1 = sub_cat.xpath(".//li[contains(@class,'li-level-3')]")
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath("a/text()").string()
                url = sub_cat1.xpath("a/@href").string()
                session.queue(Request(url + "/page=viewall"), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
            else:
                url = sub_cat.xpath("a/@href").string()
                session.queue(Request(url + "/page=viewall"), process_prodlist, dict(cat=name + '|' + sub_name))
        else:
            url = cat.xpath("a/@href").string()
            session.queue(Request(url + "/page=viewall"), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[@class='product']")
    for prod in prods:
        name = prod.xpath(".//h5/text()").string()
        url = prod.xpath(".//a/@href").string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.category = context["cat"].replace("|View All", "")
    product.url = context["url"]
    product.manufacturer = "Weber"

    ean = data.xpath("//b[contains(.,'Barcode')]/text()").string()
    if ean:
        product.properties.append(ProductProperty(type='id.ean', value=ean.replace('Barcode: ', '')))

    sku = data.xpath("//input[@name='sku']/@value").string()
    if sku:
        product.ssid = sku.replace('WEB', '')
        product.sku = product.ssid
        revs_url = "https://api.reviews.co.uk/product/review?store=wowbbq&sku=" + sku + "&mpn=&lookup=&product_group=&minRating=4&tag=&sort=undefined&per_page=100&page=1"
        session.queue(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context["product"]

    revs_json = simplejson.loads(data.content.replace('{}', ''))

    revs = revs_json["reviews"]["data"]
    for rev in revs:
        review = Review()
        review.date = rev["date_created"].split()[0]
        review.ssid = rev["product_review_id"]
        review.type = "user"
        review.url = product.url

        author = rev["reviewer"]["first_name"] + " " + rev["reviewer"]["last_name"]
        review.authors.append(Person(name=author, ssid=author))

        if 'yes' in rev['reviewer']['verified_buyer']:
            review.add_property(type='is_verified_buyer', value=True)

        if rev['votes']:
            review.add_property(type='helpful_votes', value=rev['votes'])

        review.grades.append(Grade(type="overall", value=float(rev["rating"]), best=5.0))

        excerpt = rev["review"]
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)

    if revs_json["reviews"]["to"] == 100:
        page = context.get('page', 1) + 1
        next_url = "https://api.reviews.co.uk/product/review?store=wowbbq&sku=" + product.sku + "&mpn=&lookup=&product_group=&minRating=4&tag=&sort=undefined&per_page=100&page=" + str(page)
        session.do(Request(next_url), process_reviews, dict(product=product, page=page))

    elif product.reviews:
        session.emit(product)
