from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request("https://www.volkskrant.nl/ajax/recensies/film/leesmeer/1", use="curl", force_charset="utf-8"), process_revlist, dict())


def process_revlist(data, context, session):
    name = ''
    revs = data.xpath("//h3[@class='teaser__title--compact']")
    for rev in revs:
        name = rev.xpath("descendant::text()").string(multiple=True)
        url = rev.xpath("preceding::a[1]/@href").string()
        session.queue(Request(url, use="curl", force_charset="utf-8"), process_review, dict(url=url))

    if name != context.get("name", ''):
        page = context.get("page", 1) + 1
        next_page = "https://www.volkskrant.nl/ajax/recensies/film/leesmeer/" + str(page)
        session.queue(Request(next_page, use="curl", force_charset="utf-8"), process_revlist, dict(page=page, name=name))


def process_review(data, context, session):
    product = Product()
    product.url = context["url"]
    product.ssid = context["url"].split('/')[-2].split('%')[-1]
    product.category = "Movies"

    product.name = data.xpath("//h1[contains(@class, 'artstyle__header-title')]//text()").string(multiple=True)
    if not product.name:
        product.name = data.xpath("//h4[contains(@class, 'artstyle__container__title')]//text()").string(multiple=True)
    if product.name:
        product.name = product.name.split('★')[0].strip()

    review = Review()
    review.type = "pro"
    review.title = product.name
    review.url = context["url"]
    review.ssid = product.ssid

    review.date = data.xpath("//span[@class='artstyle__byline__date']/text()").string()
    if not review.date:
        review.date = data.xpath("//span[@class='artstyle__production__date']/text()").string()

    author = data.xpath("//a[@class='artstyle__byline__author']").first()
    if not author:
        author = data.xpath("//a[@class='artstyle__production__author']").first()
    if author:
        author_name = author.xpath("text()").string()
        author_url = author.xpath("@href").string()
        if author_url and author_name:
            review.authors.append(Person(name=author_name, ssid=author_name, profile_url=author_url))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

    grade = data.xpath("//*[(self::h1 or self::p) and (contains(.,'★'))]//text()").string()
    if grade:
        value = grade.count(u'★')
        review.grades.append(Grade(type="overall", value=value, best=5))

    summary = data.xpath("//p[@class='artstyle__intro']//text()").string(multiple=True)
    if summary:
        review.add_property(type="summary", value=summary)

    excerpt = data.xpath("//p[@class='artstyle__text' or contains(@class, 'artstyle__paragraph')]//text()").string(multiple=True)
    if excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)
        session.emit(product)
