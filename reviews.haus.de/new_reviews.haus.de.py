from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.haus.de/test'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="css-1pip4vl"]')
    for cat in cats:
        name = cat.xpath('div[@class="css-60z25j"]/text()').string()

        sub_cats = cat.xpath('div/a')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = cat.xpath('@href').string()
            session.queue(Request(url), process_revlist, dict(cat=name + '|' + sub_name))


def process_revlist(data, context, session):
    revs = data.xpath('//a[contains(@class, "teaserbox")]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, url=url))

    next_url = data.xpath('//a[@rel="follow" and not(text())]/@href[contains(., "?page=")]').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    title = data.xpath('//h1[contains(@class, "chakra-heading")]/text()').string()

    product = Product()
    product.name = title.split('Test:')[-1].split('Test –')[-1]
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[@data-testid="DateTimeValue"]/text()').string()
    if date:
        review.date = date.split()[0]

    author = data.xpath('//a[contains(@href, "https://www.haus.de/autoren/") and text() and not(contains(., "Haus.de"))]/text()').string()
    author_url = data.xpath('//a[contains(@href, "https://www.haus.de/autoren/") and text() and not(contains(., "Haus.de"))]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    # summary '//div[contains(@class, "chakra-container")]//div[contains(@class, "html-text text")]/p'
