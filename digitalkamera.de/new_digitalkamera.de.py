from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.digitalkamera.de/Testbericht/0', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(., "Weitere Artikel anzeigen")]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Testbericht: ', '').replace(' im Test', '').replace(' Testbericht', '').replace(' Labortest', '').replace(' Testbilder', '').strip(' .')
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.aspx', '')
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//div[@class="teaser"]//span[@class="dkDate"]/text()').string()

    author = data.xpath('//div[@id="buch-autor"]//a[not(img)]/text()').string()
    author_url = data.xpath('//div[@id="buch-autor"]//a[not(img)]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].replace('.aspx', '')
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[@class="teaser"]/p/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//h3[@id]/following-sibling::p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
