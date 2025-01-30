from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.foto-video-sauter.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//div[@class='nav-main']//a")
    for cat in cats:
        url = cat.xpath("@href").string()
        name = cat.xpath("@title").string()
        session.queue(Request(url), process_category, dict(context, url=url, cat=name))


def process_category(data, context, session):
    cats = data.xpath("//li[@class='navigation-offcanvas-list-item navigation-offcanvas-list-item--header']/a")
    for cat in cats:
        url = cat.xpath("@href").string()
        name = cat.xpath(".//text()").string()
        session.queue(Request(url), process_category, dict(context, url=url, cat=context['cat']+'|'+name))

    if not cats:
        process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    prods = data.xpath("//a[@class='product-name']")
    for prod in prods:
        url = prod.xpath("@href").string()
        name = prod.xpath(".//text()").string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))

    next_url = data.xpath("//a[@class='page-item page-next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.ssid = data.xpath("//span[@class='product-detail-ordernumber']//text()").string()
    product.category = context['cat']
    product.url = context['url']
    product.manufacturer = data.xpath("//meta[@property='product:brand']/@content").string()
    product.sku = product.ssid

    ean_mpn = data.xpath("//p[@class='tab-collapse__ean']//text()").string(multiple=True)
    if ean_mpn:
        if "EAN/GTIN: " in ean_mpn:
            ean = ean_mpn.split("EAN/GTIN: ")[1].split(" ")[0]
            product.properties.append(ProductProperty(type='id.ean', value=ean))
        if "Herstellernummer (MPN):" in ean_mpn:
            mpn = ean_mpn.split("Herstellernummer (MPN): ")[1].split(" ")[0]
            product.properties.append(ProductProperty(type='id.manufacturer', value=mpn))

    revs = data.xpath("//div[@class='product-detail-review-item']")
    for rev in revs:
        review = Review()
        review.title = rev.xpath(".//div[contains(@class,'product-detail-review-item-title')]//text()").string(multiple=True)
        review.type = 'user'
        review.url = context['url']

        date = rev.xpath(".//div[contains(@class,'product-detail-review-item-date')]//text()").string(multiple=True)
        if date:
            review.date = " ".join(date.split(" ")[:-1])

        grade_overall = len(rev.xpath(".//*[@symbol='star-full']"))
        if grade_overall > 0:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5))

        excerpt = rev.xpath(".//p[@class='product-detail-review-item-content']//text()").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            review.ssid = review.digest(excerpt)
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
