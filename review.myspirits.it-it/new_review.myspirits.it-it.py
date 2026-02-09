from agent import *
from models.products import *


XCAT = ['HOME', 'BRAND', 'BLOG']


def run(context, session):
    session.queue(Request("https://www.myspirits.it/it/"), process_frontpage, {})


def process_frontpage(data, context, session):
    cats = data.xpath("//a[@class='amenu-link']")
    for cat in cats:
        name = cat.xpath(".//text()").string(multiple=True)
        url = cat.xpath("@href").string()

        if url and name and name not in XCAT:
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//h5[@class="product-name"]/a')
    for prod in prods:
        name = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next = data.xpath("//a[@rel='next']/@href").string()
    if next:
        session.queue(Request(next), process_prodlist, context)


def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = product.url.split('/')[-2]
    product.category = context["cat"].title()
    product.manufacturer = data.xpath("//div[contains(@class, 'product-manufacturer')]/a//text()").string()

    ean = data.xpath("//div[contains(@class, 'ean13')]/span/text()").string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type="id.ean", value=ean)

    revs_cnt = data.xpath('//h3[span[contains(text(), "Commenti")]]/span[@class]/text()').string()
    print 'revs_cnt=', revs_cnt
    if revs_cnt and int(revs_cnt.strip('( )')) > 0:
        print True

    revs_ = data.xpath('//div[@id="empty-product-comment"]')
    if revs_:
        print False

    revs = data.xpath("//div[@itemprop='review']")
    for rev in revs:
        review = Review()
        review.type = "user"
        review.title = rev.xpath(".//div[@class='title']/text()").string()
        review.date = rev.xpath(".//div[@itemprop='datePublished']/@content").string()
        review.url = product.url

        grade_overall = float(rev.xpath(".//span[@itemprop='ratingValue']/text()").string()) / 2
        if grade_overall > 0:
            review.grades.append(Grade(type="overall", value=grade_overall, best=5.0))

        author_name = rev.xpath(".//div[@itemprop='author']/text()").string()
        if author_name:
            author_name = author_name.replace("\\'", "'")
            review.authors.append(Person(name=author_name, ssid=author_name))

        excerpt = rev.xpath(".//div[@itemprop='description']//text()").string(multiple=True)
        if excerpt:
            excerpt = excerpt.replace('\\n', '').replace('\\r', '').replace("\\'", "'").replace('\\"', '"')
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest()
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
