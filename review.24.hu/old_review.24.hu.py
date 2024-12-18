from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://24.hu/tech/", use="curl"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//a[contains(@class, 'm-articleWidget__link')][normalize-space()][contains(@href, '/tech/')]")
    for rev in revs:
        name = rev.xpath("text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url, use="curl"), process_review, dict(name=name, url=url))

    next_url = data.xpath("//a[contains(@class, 'next')]/@href").string()
    if next_url:
        session.queue(Request(next_url, use="curl"), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = product.url.split('/')[-2]
    product.category = "Tech"

    review = Review()
    review.type = "pro"
    review.title = product.name
    review.ssid = product.ssid
    review.date = data.xpath("//span[contains(@class, 'o-post__date')]/text()").string().rsplit('.', 1)[0].replace(' ', '')
    review.url = product.url

    author = data.xpath("//a[@class='m-author__name']").first()
    if author:
        name = author.xpath("text()").string()
        url = author.xpath("@href").string()
        if url:
            ssid = url.split('/')[-2]
            review.authors.append(Person(name=name, ssid=ssid, profile_url=url))
        else:
            review.authors.append(Person(name=name, ssid=name))

    summary = data.xpath("//div[contains(@class, 'o-post__lead')]//text()").string(multiple=True)
    if summary:
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath("//div[contains(@class, 'o-post__body')]/p/span[@data-ce-measure-widget]/text()").string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath("//div[contains(@class, 'o-post__body')]/p[not(span[@data-ce-measure-widget])]//text()").string(multiple=True)
    if excerpt:
        review.add_property(type="excerpt", value=excerpt)
        product.reviews.append(review)
        session.emit(product)
