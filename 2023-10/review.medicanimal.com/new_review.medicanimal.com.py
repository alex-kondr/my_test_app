from agent import *
from models.products import *

import simplejson


XCAT = ["Top brands", "Offers", "Sale", "Spooky", "Food type"]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request("https://www.medicanimal.com/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath("//div[@class='nav-level-bar navigation-container']/ul/li")
    for cat in cats:
        name = cat.xpath("div[@class='text']/text()").string()

        if name not in XCAT:
            sub_cats = cat.xpath("div[contains(@class, 'nav-level-2')]//ul[@class='paws-container']/li")
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath("div[@class='text']/text()").string()

                if sub_name not in XCAT:
                    sub_cats1 = sub_cat.xpath("div[contains(@class, 'nav-level-3')]//div[@class='nav-brick']/ul/li")
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath("div[@class='text']/text()").string()

                        if sub_name1 not in XCAT:
                            sub_cats2 = sub_cat1.xpath(".//li")
                            for sub_cat2 in sub_cats2:
                                sub_name2 = sub_cat2.xpath("div[@class='text']/text()").string()
                                url = sub_cat2.xpath("a/@href").string()
                                session.queue(Request(url), process_prodlist, dict(cat=name+'|'+sub_name+'|'+sub_name1+'|'+sub_name2))


def process_prodlist(data, context, session):
    prods = data.xpath("//li[contains(@class, 'js-product-item')]")
    for prod in prods:
        name = prod.xpath("a/@data-product-name").string()
        url = prod.xpath("a/@href").string()
        manufacturer = prod.xpath("a/@data-brand").string()
        ssid = prod.xpath("a/@data-variant").string()
        grade = prod.xpath(".//div[@class='rating-stars']")

        if grade:
            session.queue(Request(url+"/reviewhtml/all/en"), process_reviews, dict(context, name=name, url=url, manufacturer=manufacturer, ssid=ssid))

    next_url = data.xpath("//a[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_reviews(data, context, session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = context["ssid"]
    product.sku = context["ssid"]
    product.category = context["cat"].replace('|All ', '|')
    product.manufacturer = context["manufacturer"]

    revs = data.xpath("//li[@class='review-entry']")
    for rev in revs:
        review = Review()
        review.type = "user"
        review.date = rev.xpath(".//span[@class='date']/text()").string()
        review.url = product.url

        title = rev.xpath("div[@class='title']/text()").string()
        if title:
            review.title = title.replace("â€™", "'").replace('â€œ', '«').replace('â€�', '»').replace('â€˜', "'").replace('â€¦', '...').replace('â€“', '-')

        author = rev.xpath(".//span[@class='author']/text()").string()
        if author:
            author = author.split("-")[0].strip()
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath("div/@data-rating").string()
        if grade_overall:
            grade_overall = simplejson.loads(grade_overall)["rating"]
            review.grades.append(Grade(type="overall", value=grade_overall, best=5.0))

        excerpt = rev.xpath("div[@class='content']//text()").string(multiple=True)
        if excerpt:
            excerpt = excerpt.replace("â€™", "'").replace('â€œ', '«').replace('â€�', '»').replace('â€˜', "'").replace('â€¦', '...').replace('â€“', '-')
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
