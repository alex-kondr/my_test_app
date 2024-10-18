from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request("http://androidinsider.ru/", use="curl"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//ul[@id='menu-trendy']/li/a")
    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()
        session.queue(Request(url, use="curl"), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    prods = data.xpath("//h2[@class='post-title']/a")
    for prod in prods:
        name = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url, use="curl"), process_product, dict(context, name=name, url=url))

    next_page = data.xpath("//a[@rel='next']/@href").string()
    if next_page:
        session.queue(Request(next_page, use="curl"), process_revlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = context["url"].split('/')[-1].split('.')[0]
    product.category = context["cat"]

    review = Review()
    review.type = "pro"
    review.title = context["name"]
    review.url = context["url"]
    review.ssid = product.ssid

    date = data.xpath("//time/@datetime").string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("//a[contains(@class, 'author-name')]").first()
    if author:
        name = author.xpath(".//text()").string(multiple=True)
        url = author.xpath("@href").string()
        review.authors.append(Person(name=name, ssid=name, profile_url=url))

    conclusion = data.xpath("//div[@class='article-body']//h2[regexp:test(., 'Выводы')]/following-sibling::p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath("//div[@class='article-body']/p//text()").string(multiple=True)
    if excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)
        session.emit(product)
