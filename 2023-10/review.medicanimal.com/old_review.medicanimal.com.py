from agent import *
from models.products import *
import simplejson


XCAT = ["Top brands", "Services"]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request("https://www.medicanimal.com/", use="curl"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats1 = data.xpath("//div[@class='nav-level-bar navigation-container']/ul/li")
    for cat1 in cats1:
        cat1_name = cat1.xpath("div[@class='text']/text()").string()
        cats2 = cat1.xpath("div[contains(@class, 'nav-level-2')]//ul[@class='paws-container']/li")
        for cat2 in cats2:
            cat2_name = cat2.xpath("div[@class='text']/text()").string()
            if cat2_name in XCAT:
                continue
            cats3 = cat2.xpath("div[contains(@class, 'nav-level-3')]//div[@class='nav-brick']/ul/li")
            for cat3 in cats3:
                cat3_name = cat3.xpath("div[@class='text']/text()").string()
                if cat3_name in XCAT:
                    continue
                cats4 = cat3.xpath(".//li")
                for cat4 in cats4:
                    cat4_name = cat4.xpath("div[@class='text']/text()").string()
                    url = cat4.xpath("a/@href").string()
                    session.queue(Request(url, use="curl"), process_prodlist, dict(cat=cat1_name+'|'+cat2_name+'|'+cat3_name+'|'+cat4_name))


def process_prodlist(data, context, session):
    prods = data.xpath("//li[contains(@class, 'js-product-item')]")
    for prod in prods:
        name = prod.xpath("a/@data-product-name").string()
        url = prod.xpath("a/@href").string()
        brand = prod.xpath("a/@data-brand").string()
        ssid = prod.xpath("a/@data-variant").string()
        grade = prod.xpath(".//div[@class='rating-stars']")
        if grade:
            session.queue(Request(url+"/reviewhtml/all/en", use="curl"), process_reviews, dict(context, name=name, url=url, brand=brand, ssid=ssid))

    next_page = data.xpath("//a[@rel='next']/@href").string()
    if next_page:
        session.queue(Request(next_page, use="curl"), process_prodlist, dict(context))


def process_reviews(data, context, session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = context["ssid"]
    product.category = context["cat"]
    product.manufacturer = context["brand"]

    revs = data.xpath("//li[@class='review-entry']")
    for rev in revs:
        review = Review()
        review.type = "user"
        review.title = rev.xpath("div[@class='title']/text()").string()
        review.date = rev.xpath(".//span[@class='date']/text()").string()
        review.url = product.url

        grade_overall = rev.xpath("div/@data-rating").string()
        if grade_overall:
            grade_overall = simplejson.loads(grade_overall)["rating"]
            review.grades.append(Grade(type="overall", value=grade_overall, best=5.0))

        author_name = rev.xpath(".//span[@class='author']/text()").string()
        if author_name:
            author_name = author_name.split("-")[0].strip()
            review.authors.append(Person(name=author_name, ssid=author_name))

        excerpt = rev.xpath("div[@class='content']//text()").string(multiple=True)
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest()
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
