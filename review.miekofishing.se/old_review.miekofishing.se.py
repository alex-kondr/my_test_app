from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request('https://www.miekofishing.se/'), process_frontpage, {})


def process_frontpage(data, context, session):
    cats = data.xpath("//ul[@class='mu_level_1']/li[@class='ml_level_1']/a")
    for cat in cats:
        url = cat.xpath('@href').string()
        name = cat.xpath('.//text()').string()
        session.queue(Request(url), process_category, dict(cat=name))


def process_category(data, context, session):
    cats = data.xpath("//h5/a[@class='subcategory-name']")
    for cat in cats:
        url = cat.xpath("@href").string()
        name = cat.xpath(".//text()").string()
        category = context['cat'] + '|' + name
        session.queue(Request(url), process_subcategory, dict(context, cat=category))


def process_subcategory(data, context, session):
    prods = data.xpath("//div[@class='product-container']//a[@class='product-name']")
    for prod in prods:
        url = prod.xpath(".//@href").string()
        title = prod.xpath(".//text()").string()
        session.queue(Request(url), process_review, dict(context, url=url, title=title))

    nexturl = data.xpath("//ul[@class='pagination']/li[@id='pagination_next_bottom']/a/@href").string()
    if nexturl:
        session.queue(Request(nexturl), process_subcategory, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.sku = data.xpath("//p[@id='product_suppliernr']/span[@class='editable']/text()").string()
    product.ssid = product.sku
    product.category = context['cat']
    product.url = context['url']
    product.manufacturer = data.xpath("//p[@id='product_manufacturer']/span[@class='editable']/a/text()").string()

    revs = data.xpath("//body/p[@class='title_block']")
    for rev in revs:
        review = Review()
        review.title = rev.xpath(".//text()").string(multiple=True)
        review.type = 'user'
        review.url = context['url']
        review.date = rev.xpath("./../following-sibling::head[1]/meta[@itemprop='datePublished']/@content").string()

        author_name = rev.xpath("./../div/span[@itemprop='author']//text()").string()
        review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = rev.xpath("./../preceding-sibling::head[1]/meta[@itemprop='ratingValue']/@content").string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath("./../following-sibling::body[1]/p[@itemprop='reviewBody']//text()").string(
            multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            review.ssid = product.ssid + '-' + review.date + '-' + author_name
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
