from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://eisa.eu/awards/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath("//ul[@class='awards']/li/a[normalize-space()]")
    for cat in cats:
        name = cat.xpath("text()").string(multiple=True)
        url = cat.xpath("@href").string()
        session.queue(Request(url), process_awards, dict(cat=name))


def process_awards(data, context, session):
    awards = data.xpath("//ul[@class='awards']/li[@class='awards-box']")
    for award in awards:
        name = award.xpath(".//p[@class='title']/text()").string()
        url = award.xpath("a/@href").string()
        session.queue(Request(url), process_award, dict(context, name=name, url=url))


def process_award(data, context, session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = product.url.split('/')[-2]
    product.category = context["cat"]

    review = Review()
    review.title = product.name
    review.type = "pro"
    review.url = context["url"]
    review.ssid = product.ssid

    award_name = data.xpath("//h1[@class='award-title']/span[@class='subtitle']/text()").string()
    award = {"url": context["url"], "name": award_name}
    review.add_property(type="awards", value=award)

    excerpt = data.xpath("//div[@class='content']/p//text()").string(multiple=True)
    if excerpt:
        review.add_property(type="excerpt", value=excerpt)
        product.reviews.append(review)
        session.emit(product)
