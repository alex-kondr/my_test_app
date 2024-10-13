from agent import *
from models.products import *


XCAT = ["Contact"]


def run(context, session):
    session.queue(Request("http://www.obiwi.fr/", use="curl"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//ul[@id='menu-menu-1']/li/a")
    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()
        if cat not in XCAT:
            session.queue(Request(url, use="curl"), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath("//h1[contains(@class, 'post-header-title')]/a")
    for rev in revs:
        name = rev.xpath("text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url, use="curl"), process_review, dict(context, name=name, url=url))

    next_url = data.xpath("//link[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url, use="curl"), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = context["cat"]

    review = Review()
    review.type = 'pro'
    review.ssid = product.ssid
    review.title = context['name']
    review.url = context['url']
    review.date = data.xpath("//div[contains(@class, 'post-info')]/span/text()").string()

    author = data.xpath("//div[@class='post-info clearfix']/span[2]").first()
    if author:
        name = author.xpath("text()").string()
        review.authors.append(Person(name=name, ssid=name))

    excerpt = data.xpath("//div[@class='entry-content']/*[self::p or self::ul]//text()").string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

    product.reviews.append(review)
    session.emit(product)
