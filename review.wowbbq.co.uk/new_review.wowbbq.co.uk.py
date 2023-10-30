from agent import *
from models.products import *

import simplejson


XCAT = ['Weber BBQ Clearance', 'View All']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.wowbbq.co.uk/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath("//li[contains(@class,'li-level-1')]")
    for cat in cats:
        name = cat.xpath("a/text()").string()

        if name not in XCAT:
            sub_cats = cat.xpath(".//li[contains(@class,'li-level-2')]")
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath("a/text()").string()

                sub_cats1 = sub_cat.xpath(".//li[contains(@class,'li-level-3')]")
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath("a/text()").string()

                    if sub_name1 not in XCAT:
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
    product.category = context["cat"]
    product.url = context["url"]
    product.manufacturer = "Weber"

    ean = data.xpath("//b[contains(.,'Barcode')]/text()").string()
    if ean:
        product.properties.append(ProductProperty(type='id.ean', value=ean.replace('Barcode: ', '')))

    ssid = data.xpath("//input[@name='sku']/@value").string()
    if ssid:
        product.ssid = ssid.replace('WEB', '')
        revs_url = "https://api.reviews.co.uk/product/review?store=wowbbq&sku=" + ssid + "&sort=undefined&per_page=100&page=1"
        session.queue(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context["product"]

    revs_json = simplejson.loads(data.content.replace('{}', ''))

    revs = revs_json.get("reviews", {}).get("data", [])
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url

        date = rev.get("date_created")
        if date:
            review.date = date.split()[0]

        first_name = rev.get("reviewer", {}).get("first_name")
        last_name = rev.get("reviewer", {}).get("last_name")
        author = ''
        if first_name:
            author += first_name
        if last_name:
            author += ' ' + last_name

        if author:
            review.authors.append(Person(name=author, ssid=author))

        if 'yes' in rev.get('reviewer', {}).get('verified_buyer', ''):
            review.add_property(type='is_verified_buyer', value=True)

        helpful_votes = rev.get('votes')
        if helpful_votes:
            review.add_property(type='helpful_votes', value=int(helpful_votes))

        grade = rev.get("rating")
        if grade:
            review.grades.append(Grade(type="overall", value=float(grade), best=5.0))

        excerpt = rev.get("review")
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            ssid = rev.get("product_review_id")
            if ssid:
                review.ssid = str(ssid)
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if revs_json.get("reviews", {}).get("to", 0) == 100:
        page = context.get('page', 1) + 1
        next_url = "https://api.reviews.co.uk/product/review?store=wowbbq&sku=" + product.ssid + "&sort=undefined&per_page=100&page=" + str(page)
        session.do(Request(next_url, use='curl'), process_reviews, dict(product=product, page=page))

    elif product.reviews:
        session.emit(product)
