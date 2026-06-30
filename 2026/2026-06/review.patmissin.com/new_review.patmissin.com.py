from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://patmissin.com/reviews/reviews.html'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(., "Harmonicas")]/following-sibling::p/a[not(contains(., "Return to Main Inde"))]')
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(name=name, url=url))

    # no next page


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '')
    product.category = 'Harmonicas'

    for imgs in data.xpath("//img[contains(@src,'.jpg')]"):
        img = imgs.xpath("@src").string()
        if img:
           product.add_property(type="image", value=dict(src=img))

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1/text()').string()
    review.url = product.url
    review.ssid = product.ssid

    excerpt = data.xpath('//body/p[not(contains(., "For more details"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
