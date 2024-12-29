from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://zwergperten.de/Kindersitze/Babyschale/'), process_prodlist, dict(cat="Kindersitze|Babyschale"))
    session.queue(Request('https://zwergperten.de/Kindersitze/Babyschale/Zubehoer-Babyschale/'), process_prodlist, dict(cat="Kindersitze|Babyschale|Zubehör Babyschale"))
    session.queue(Request('https://zwergperten.de/Kindersitze/Reboarder-I-Kleinkindsitz/'), process_prodlist, dict(cat="Kindersitze|Reboarder I Kleinkindsitz"))
    session.queue(Request('https://zwergperten.de/Kindersitze/Reboarder-I-Kleinkindsitz/Zubehoer-Kleinkindsitz/'), process_prodlist, dict(cat="Kindersitze|Reboarder I Kleinkindsitz|Zubehör Kleinkindsitz"))
    session.queue(Request('https://zwergperten.de/Kindersitze/Folgesitz-I-Kindersitz/'), process_prodlist, dict(cat="Kindersitze|Folgesitz I Kindersitz"))
    session.queue(Request('https://zwergperten.de/Kindersitze/Folgesitz-I-Kindersitz/Zubehoer-Kindersitz/'), process_prodlist, dict(cat="Kindersitze|Folgesitz I Kindersitz|Zubehör Kindersitz"))


def process_prodlist(data, context, session):
    revs = data.xpath('//div[@class="product-info"]/a')
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    if data.xpath('//input[@id="p-next-bottom" and not(@disabled)]'):
        next_page = context.get('page', 1) + 1
        next_url = data.response_url.split('?p=')[0] + "?p=" + str(next_page)
        session.queue(Request(next_url), process_prodlist, dict(context, page=next_page))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']
    product.sku = product.url.split('/')[-1]
    product.manufacturer = data.xpath('//a[@class="product-detail-manufacturer-link"]/@title').string()

    mpn = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[contains(@class, "review-item-info")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//p/small/text()').string()
        if date:
            review.date = date.rsplit(' ', 1)[0]

        author = rev.xpath('(preceding::div[@itemprop="author"])[1]//text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//use[@xlink_href="#icons-solid-star"])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.xpath('.//p[@class="h5"]//text()').string(multiple=True)
        excerpt = rev.xpath('(following-sibling::p[contains(@class, "review-item-content")])[1]//text()').string(multiple=True)
        if excerpt:
            review.title= title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page