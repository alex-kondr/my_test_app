from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request("https://milex.co.za/", use="curl", force_charset="utf-8"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats1 = data.xpath("//li[contains(@class, 'lvl1 parent dropdown')]//ul/li")
    for cat1 in cats1:
        cat1_name = cat1.xpath(".//a[contains(@class, 'site-nav lvl-1')]/text()").string()
        if cat1_name != "View the Milex Range":
            url = cat1.xpath(".//a[contains(@class, 'site-nav lvl-1')]/@href").string()
            session.queue(Request(url, use="curl", force_charset="utf-8"), process_prodlist, dict(cat=cat1_name, url=url))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[contains(@class, 'grid grid--uniform grid-products grid--view-items')]/div")
    for prod in prods:
        name = prod.xpath(".//a[contains(@class, 'grid-view-item__title')]/text()").string()
        url = prod.xpath(".//a[contains(@class, 'grid-view-item__title')]/@href").string()
        ssid = prod.xpath(".//span[@class='shopify-product-reviews-badge']/@data-id").string()

        rating = prod.xpath(".//span[contains(@class, 'jdgm-prev-badge__text')]/text()")
        if url and rating != "No reviews":
            session.queue(Request(url, use="curl", force_charset="utf-8"), process_product, dict(context, name=name, url=url, ssid=ssid))

    if prods:
        page = context.get("page", 1) + 1
        next_url = context['url'] + "?page=" + str(page)
        session.queue(Request(next_url, use="curl", force_charset="utf-8"), process_prodlist, dict(context, page=page))
        

def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = context["ssid"]
    product.category = context["cat"]
    product.manufacturer = "Milex"
    
    revs_url = "https://judge.me/reviews/reviews_for_widget?url=milex-south-africa.myshopify.com&shop_domain=milex-south-africa.myshopify.com&platform=shopify&page=" 
    session.do(Request(revs_url + '1' + "&per_page=5&product_id=" + context["ssid"], use="curl", force_charset="utf-8"), process_reviews, dict(product=product, revs_url=revs_url, ssid_2=context["ssid"]))
    

def process_reviews(data, context, session):
    product = context["product"]

    json = simplejson.loads(data.content.replace("{}\r\n", ''))
    html = data.parse_fragment(json["html"])

    revs = html.xpath("//div[@class='jdgm-rev-widg__reviews']/div")
    for rev in revs:
        review = Review()
        review.type = "user"
        review.title = rev.xpath(".//b[@class='jdgm-rev__title']/text()").string()
        review.ssid = rev.xpath("@data-review-id").string()
        review.url = product.url

        review.date = rev.xpath(".//span[contains(@class, 'jdgm-rev__timestamp')]/@data-content").string()
        if review.date:
            review.date = review.date.split(' ')[0]

        is_verified_buyer = rev.xpath("@data-verified-buyer").string()
        if is_verified_buyer == "true":
            review.add_property(type="is_verified_buyer", value=True)
        else:
            continue

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
    
    ssid_2 = context["ssid_2"]
    if revs:
        page = context.get("page", 1) + 1
        session.do(Request(context["revs_url"] + str(page) + "&per_page=5&product_id=" + ssid_2, use="curl", force_charset="utf-8"), process_reviews, dict(context, page=page))

    elif product.reviews:
        session.emit(product)
