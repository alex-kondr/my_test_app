from agent import *
from models.products import *


def process_frontpage(data, context, session):
    for cat in data.xpath("//a[span//text()[contains(.,'reviews)')]]"):
        name = cat.xpath("span[1]//text()").string()
        url = cat.xpath("@href").string()
        session.queue(Request(url), process_prodlist, dict(url=url, cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath("//div/ul[@id='products-list']/li/a")
    for prod in prods:
        name = prod.xpath(".//span[@class='hidden-desktop']//text()").string(multiple=True).strip()
        url = prod.xpath("@href").string()
        no_revs = prod.xpath(".//svg[@name='stars-0']")
        if not no_revs:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next = data.xpath("//li[@class='next']/a//@href").string()
    if next:
        session.queue(Request(next), process_prodlist, context)


def process_product(data, context, session):
    product = context.get("product")
    if not product:
        product = Product()
        product.name = context["name"]
        product.category = context["cat"] + "|" + data.xpath("//li[@class='visible-on-mobile category']//text()").string(multiple=True) or "Baby products"
        product.url = context["url"].split(".html")[0]
        product.ssid = product.url.split("/")[-1]
        product.manufacturer = data.xpath("//a[@class='h1 brand-name']//text()").string(multiple=True)

    revs = data.xpath("//head[meta[@itemprop='ratingValue']]")
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = context["url"]
        review.title = rev.xpath("preceding-sibling::body[3]//div[@class='review-text']//strong//text()").string(multiple=True)
        review.date = rev.xpath("preceding-sibling::head[2]//meta//@content").string()

        author = rev.xpath("preceding-sibling::body[3]//span[@itemprop='author']//text()").string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        pros = rev.xpath("following-sibling::body[1]//li[@class='pros']//text()")
        if pros:
            pros = pros.string(multiple=True).replace("Strengths:", "").strip()
            review.add_property(type="pros", value=pros)

        cons = rev.xpath("following-sibling::body[1]//li[@class='cons']//text()")
        if cons:
            cons = cons.string(multiple=True).replace("Weaknesses:", "").strip()
            review.add_property(type="cons", value=cons)

        grade = rev.xpath("meta[@itemprop='ratingValue']//@content").string()
        if grade:
            review.grades.append(Grade(type="overall", value=float(grade), best=5.0))

        grades = rev.xpath("following-sibling::body[1]//ul[@class='details']/li")
        for grade in grades:
            grade_name = grade.xpath(".//span[@class='label']//text()").string()
            grade_val = grade.xpath(".//span[@class='value']/svg//@name").string().split("stars-")[-1]
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

        excerpt = rev.xpath("following-sibling::body[1]//div[@itemprop='reviewBody']//text()").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

            review.ssid = review.digest()
            product.reviews.append(review)

    next_url = data.xpath("//a[@rel='next']//@href").string()
    if next_url:
        session.do(Request(next_url), process_product, dict(context, product=product))
    elif product.reviews:
        session.emit(product)


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request("https://www.consobaby.co.uk"), process_frontpage, dict())
