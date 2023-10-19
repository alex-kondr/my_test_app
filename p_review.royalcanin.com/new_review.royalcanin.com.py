from agent import *
from models.products import *
import simplejson


XCAT = ["Cats", "Dogs"]


def run(context, session):
    session.queue(Request("https://www.royalcanin.com/us", use="curl"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//li[contains(@class, 'rc-list__item rc-list__item--group')]")
    for cat in cats:
        name = cat.xpath("div/a/@title").string()
        url = cat.xpath("ul/li[1]/a/@href").string()
        if not url:
            url = cat.xpath("div/a/@href").string()
        if name in XCAT:
            session.queue(Request(url, use="curl"), process_subcatlist, dict(cat=name))


def process_subcatlist(data, context, session):
    subcats = data.xpath("//div[@class='rc-full-width rc-text--left']//a[contains(@class, 'rc-btn rc-btn--') and not(@id)]")
    for subcat in subcats:
        name = context["cat"] + '|' + subcat.xpath("text()").string().split("All ")[-1].title()
        url = subcat.xpath("@href").string()
        session.queue(Request(url, use="curl"), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[@class='rc-column'][a]")
    for prod in prods:
        cat_info = prod.xpath("a/@data-product-details").string()
        cat = simplejson.loads(cat_info)
        cat = context["cat"] + '|' + cat["category"].split('/')[-1]
        info = prod.xpath("script[contains(text(), '\"@type\":\"Product\"')]/text()").string()
        info = simplejson.loads(info)
        url = prod.xpath("a/@href").string()
        rating = info.get("aggregateRating")
        if rating:
            session.queue(Request(url, use="curl"), process_product, dict(cat=cat, url=url))

    next_url = data.xpath("//button[@rel='next']/following::a[@class='rc-btn'][2]/@href").string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_prodlist, dict(context))


def process_product(data, context, session):
    info = data.xpath("//script[contains(text(), '\"@type\":\"Product\"')]/text()").string()
    info = simplejson.loads(info)

    product = Product()
    product.name = info["name"]
    product.url = context["url"]
    product.ssid = info["productID"]
    product.sku = info["sku"]
    product.category = context["cat"]
    product.manufacturer = info["brand"]["name"]
    
    revs = info["review"]
    if type(revs) is dict:
        revs = [revs]
    for rev in revs:
        review = Review()
        review.type = "user"
        review.title = rev["name"]
        review.date = rev["datePublished"].split('T')[0]
        review.url = product.url

        overall = rev["reviewRating"]["ratingValue"]
        review.grades.append(Grade(type="overall", value=overall, best=5.0))

        author = rev["author"]["name"]
        if author:
            review.authors.append(Person(name=author, ssid=author))

        excerpt = rev["reviewBody"]
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            if author:
                review.ssid = review.digest()
            else:
                review.ssid = review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
