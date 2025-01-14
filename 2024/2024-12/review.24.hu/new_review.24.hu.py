from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://24.hu/tech/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="m-articleWidget__link" and contains(@href, "https://24.hu/tech/")]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('//h1[@class="o-post__title"]//text()').string(multiple=True).replace(u'\uFEFF', '')
    product.url = context["url"]
    product.ssid = product.url.split('/')[-2]
    product.category = "Tech"

    review = Review()
    review.type = "pro"
    review.title = product.name
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath("//span[contains(@class, 'o-post__date')]/text()").string()
    if date:
        review.date = date.rsplit('.', 1)[0].replace(' ', '')

    author = data.xpath('//a[@class="m-author__authorWrap" and not(contains(@href, "24hu"))]//text()').string(multiple=True)
    author_url = data.xpath('//a[@class="m-author__authorWrap" and not(contains(@href, "24hu"))]/@href').string()
    if author and author_url:
        ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath("//div[contains(@class, 'o-post__lead')]//text()").string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '')
        review.add_property(type="summary", value=summary)

    excerpt = data.xpath('//div[@class="u-onlyArticlePages"]/p[not(contains(., "(Technet.hu)") or contains(., "linkek:"))]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '')
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
