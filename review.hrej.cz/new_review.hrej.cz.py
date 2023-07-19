from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://hrej.cz/games"), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath("//div[@class='un-card__content']")
    for prod in prods:
        name = prod.xpath(".//h3//text()").string()
        url = prod.xpath(".//a/@href").string()
        session.queue(Request(url+"/articles"), process_product, dict(context, name=name, url=url))

    next_url = data.xpath("//button/@data-load-page").string()
    if next_url:
        next_url = "https://hrej.cz/games?page=" + str(int(next_url)+1)
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.ssid = context["url"].split('/')[-1]
    product.url = context["url"]

    manufacturer = data.xpath("//span[contains(.,'Vydavatel')]//text()").string()
    if manufacturer:
        product.manufacturer = manufacturer.replace("Vydavatel", '')

    category = data.xpath("//span[@class='un-chip__text']//text()").string()#########################
    if category:
        product.category = "Games|" + category
    else:
        product.category = "Games"

    reviews = data.xpath("//a[@class='un-card-headline']/@href")
    for rev in reviews:
        session.do(Request(rev.string()), process_review, dict(context, product=product, rev_url=rev.string()))

    if product.reviews:
        session.emit(product)


def process_review(data, context, session):
    product = context["product"]

    review = Review()
    review.title = data.xpath("//h1[@class='post-header__title']//text()").string()
    review.ssid = context["rev_url"].split('/')[-1]
    review.type = "pro"
    review.url = context["rev_url"]

    date = data.xpath("//div[@class='post-header-info__content post-header-info__content--with-profile']/span//text()").string(multiple=True)
    if date:
        review.date = ''.join(date.split(' ')[:3])

    authors = data.xpath("//div[@class='post-header-info__name']")
    if not authors:
        authors = data.xpath("//p[@class='post-header-info__name']")
    for author in authors:
        author_name = author.xpath(".//a/text()").string()
        if author_name:###############################
            author_url = author.xpath(".//a/@href").string()
            review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_url.split('/')[-1]))

    grade_overall = data.xpath("//div[contains(@class,'review-rating')]/@data-rating").string()
    if grade_overall:
        review.grades.append(Grade(type="overall", value=float(grade_overall)/10, best=10.0))

    pages = data.xpath("//a[contains(@class,'post-chapters__item')]")
    if pages:
        for page in pages:
            title = page.xpath("text()").string()
            url = page.xpath("@href").string()
            review.add_property(type="pages", value=dict(url=url, title=title))
        session.do(Request(url), process_lastpage, dict(context, review=review))

        summary = data.xpath("//div[@class='post-body']/p//text()").string(multiple=True)
        if summary:
            review.add_property(type="summary", value=summary)
            product.reviews.append(review)
    else:
        summary = data.xpath("//div[@class='post-body__perex']/p//text()").string(multiple=True)
        if summary:
            review.add_property(type="summary", value=summary)

        conclusion = data.xpath("//div[@class='review-box__verdict']//p//text()").string(multiple=True)
        if conclusion:
            review.add_property(type="conclusion", value=conclusion)

        excerpt = data.xpath("//div[@class='post-body']/p//text()").string(multiple=True)
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)
            product.reviews.append(review)


def process_lastpage(data, context, session):
    review = context["review"]

    grade_overall = data.xpath("//div[contains(@class,'review-rating')]/@data-rating").string()
    if grade_overall:
        review.grades.append(Grade(type="overall", value=float(grade_overall)/10, best=10.0))

    conclusion = data.xpath("//div[@class='review-box__verdict']//p//text()").string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)
