from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.netties.be/index.php?arc=Hardware&arc_start=0', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//li[@class="lijst_archief"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        if title and url:
            session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//button[contains(., "Volgende pagina")]/@onclick').string()
    if next_url:
        next_url = next_url.replace("location.href='", "").replace("';", "")
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = 'Hardware'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//p[@id="gepubliceerd"]/text()').string()
    if date:
        review.date = date.split()[-1]

    excerpt = data.xpath('//div[contains(@id, "tekst_prom")]/a[@class="link_tekst"]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
