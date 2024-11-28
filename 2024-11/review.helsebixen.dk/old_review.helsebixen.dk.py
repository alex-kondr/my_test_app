from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.helsebixen.dk/"), process_frontpage, {})


def process_frontpage(data, context, session):
    cats = data.xpath("//ul[@id='firtalNav']//a[@class='firtalMenuPoint']")
    for cat in cats:
        url = cat.xpath("@href").string()
        if url and "brands" not in url:
            session.queue(Request(url), process_categories, dict(context, url=url))


def process_categories(data, context, session):
    try:
        urls = data.xpath("//a[@class='product-image']")
        if not urls:
            urls = data.xpath("//ul[@class='large-category-list']/following-sibling::a")
    except:
        print("Exception.")
        return

    for url in urls:
        title = url.xpath("@title").string()
        url = url.xpath("@href").string()
        if url and title:
            session.queue(Request(url), process_product, dict(context, url=url))
        elif url and "brands" not in url:
            session.queue(Request(url), process_categories, dict(context, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = data.xpath("//h1[@class='product-name']//text()").string(multiple=True)
    product.sku = data.xpath("//span[@itemprop='sku']//text()").string()
    product.ssid = product.sku
    product.description = data.xpath("//div[@class='short-description show-only-on-large']//text()").string(multiple=True)
    product.category = data.xpath("//li[@class='home']/a/span//text()").string(multiple=True)
    product.url = context["url"]

    ean = data.xpath("//span[@itemprop='gtin13']//text()").string()
    if ean:
        product.add_property(type="id.ean", value=ean)

    reviews = data.xpath("//div[@itemprop='review']")
    for rev in reviews:
        review = Review()
        review.type = "user"

        author = rev.xpath(".//span[@class='review-by']//span//text()").string()
        review.authors.append(Person(name=author, ssid=author))

        grade = rev.xpath(".//div[@class='rating']/@style").string()
        grade = float(grade.split("width:")[1].split("%")[0]) / 20
        review.grades.append(Grade(name="Stjerner", type="overall", value=grade, best=5.0))
        
        summary = rev.xpath(".//div[@class='review-subject']//text()").string(multiple=True)
        if summary:
            review.properties.append(ReviewProperty(type="summary", value=summary))

        excerpt = rev.xpath(".//div[@class='review-text']//text()").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

        review.ssid = product.ssid + author

        review.url = context["url"]

        if summary or excerpt:
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
