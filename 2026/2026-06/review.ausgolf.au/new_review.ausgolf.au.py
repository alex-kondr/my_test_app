from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://www.ausgolf.com.au/golf-equipment", use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//p[contains(., "LATEST RELEASES")]/following-sibling::p//a[.//text() and not(contains(., "SEE MORE") or contains(., "More Details") or img)]')
    for rev in revs:
        name = rev.xpath(".//text()").string(multiple=True)
        url = rev.xpath("@href").string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, name=name, url=url))

    # no next page


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = 'Golf Equipment'

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[contains(@class, "title")]/text()').string()
    review.ssid = product.ssid
    review.url = context['url']

    excerpt = data.xpath('//div[h1[contains(@class, "title")]]/p[not(contains(., "Recommended Retail Pricing"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
