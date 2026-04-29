from agent import *
from models.products import *
import time


SLEEP = 2


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://sg.hu/', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    time.sleep(SLEEP)

    cats = data.xpath('//div[contains(@class, "items-center") and nav]/a[contains(@class, "items-center") and text()]')
    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()
        session.queue(Request(url, max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    time.sleep(SLEEP)

    revs = data.xpath('//div[h4 and a]')
    for rev in revs:
        title = rev.xpath("h4/text()").string()
        url = rev.xpath("a/@href").string()
        session.queue(Request(url, max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[contains(text(), "Következő oldal")]/@href').string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    time.sleep(SLEEP)

    product = Product()
    product.name = context["title"]
    product.url = context["url"]
    product.ssid = product.url.split('/')[-1]
    product.category = context["cat"]

    review = Review()
    review.type = "pro"
    review.title = context["title"]
    review.ssid = product.ssid
    review.url = product.url

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    excerpt = data.xpath('//div[contains(@class, "Article")]/div//text()').string(multiple=True)
    if excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
