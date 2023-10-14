from agent import *
from models.products import *
import simplejson


XCAT = ["Offers", "New In", "Brands", "Blog", "Bestsellers ", "Top Brands"]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.salonsdirect.com/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats1 = data.xpath("//ul[@class='site-nav__list']/li")
    for cat1 in cats1:
        cat1_name = cat1.xpath("a//text()").string(multiple=True)
        if not cat1_name:
            cat1_name = cat1.xpath("span/text()").string()

        if cat1_name not in XCAT:
            url = cat1.xpath("a/@href").string()
            cats2 = cat1.xpath("ul/li")
            for cat2 in cats2:
                cat2_name = cat2.xpath("a//text()").string(multiple=True)
                url = cat2.xpath('a/@href').string()

                if cat2_name not in XCAT:
                    cats3 = cat2.xpath("ul/li[position() > 1]/a")
                    for cat3 in cats3:
                        cat3_name = cat3.xpath(".//text()").string(multiple=True)
                        url = cat3.xpath("@href").string()
                        session.queue(Request(url), process_prodlist, dict(cat=cat1_name+'|'+cat2_name+'|'+cat3_name))
                    else:
                        session.queue(Request(url), process_prodlist, dict(cat=cat1_name+'|'+cat2_name))
            else:
                session.queue(Request(url), process_prodlist, dict(cat=cat1_name))


def process_prodlist(data, context, session):
    prods = data.xpath("//ol[contains(@class, 'product-items')]/li/div")
    for prod in prods:
        name = prod.xpath(".//a[@class='product-item-link']/text()").string()
        ssid = prod.xpath(".//div/@data-product-id").string()
        url = prod.xpath(".//a[@class='product-item-link']/@href").string()

        session.queue(Request(url), process_product, dict(context, name=name, ssid=ssid, url=url))

    next_url = data.xpath("//link[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = context["ssid"]
    product.category = context["cat"]
    product.sku = data.xpath("//div[strong[@class='type' and text()='Product code:']]/div/text()").string()

    url = "https://api.feefo.com/api/10/reviews/product?page_size=10&since_period=ALL&full_thread=exclude&unanswered_feedback=include&source=on_page_product_integration&sort=-updated_date&feefo_parameters=include&media=include&merchant_identifier=salons-direct&origin=www.salonsdirect.com&product_sku=" + product.sku + "&page="
    session.queue(Request(url+'1'), process_product, dict(product=product))


def process_review(data, context, session):
    product = context["product"]
    revs_json = simplejson.loads(data.raw)

    revs = revs_json.get("productReviews", {}).get("reviews", {})
    for rev in revs:
        review = Review()
        review.type = "user"
        review.date = rev["createdAt"].split('T')[0]
        review.url = product.url

        grade_overall = rev["products"][0].get("rating", {}).get("rating")
        if grade_overall:
            review.grades.append(Grade(type="overall", value=grade_overall, best=5))

        author_name = rev.get("customer", {}).get("display_name")
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        excerpt = rev["products"][0].get("review")
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    total_pages = json["summary"]["meta"]["pages"]
    page = context.get("page", 1)
    if page < total_pages:
        session.do(Request(context["revs_url"]+str(page+1)), process_review, dict(context, page=page+1))
    elif product.reviews:
        session.emit(product)
