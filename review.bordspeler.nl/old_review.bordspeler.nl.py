from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://bordspeler.nl/recensies/"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//a[@class='entry-title-link']")
    for rev in revs:
        name = rev.xpath("text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_review, dict(name=name, url=url))

    next_url = data.xpath("//li[@class='pagination-next']/a/@href").string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Games'

    product.manufacturer = data.xpath("//div[@class='content-box-yellow']/div[contains(@class, 'first')]/text()[regexp:test(., 'auteur', 'i')]").string()
    if product.manufacturer:
        product.manufacturer = product.manufacturer.split(':')[-1].strip()
    if not product.manufacturer:
        product.manufacturer = data.xpath("//div[@class='content-box-yellow']/div[contains(@class, 'first')]/text()[regexp:test(., 'auteur', 'i')]/following-sibling::a[1]/text()").string().strip()

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath("//span[contains(@class, 'published time')]/@title").string().split('T')[0]

    author = data.xpath("//span[contains(@class, 'author')]//a").first()
    if author:
        name = author.xpath("text()").string()
        url = author.xpath("@href").string()
        ssid = url.split('/')[-2]
        review.authors.append(Person(name=name, ssid=ssid, profile_url=url))

    conclusion = data.xpath("//div[@class='entry-content']/*[contains(local-name(), 'h')][regexp:test(., '^ten slotte', 'i')]/following-sibling::p[normalize-space()]//text()").string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath("//div[@class='entry-content']/*[self::p[normalize-space()] or self::ul]//text()").string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.split(conclusion.strip())[0]
        excerpt = excerpt.strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)
        session.emit(product)
