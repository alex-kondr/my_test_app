from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://robotreviews.com/robot/', use='curl', force_charset='utf-8'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//h3/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(name=name, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict())


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.ssid = context['url'].split('/')[-2]
    product.sku = data.xpath('//tr[contains(@class, "attribute_UPC")]/td[contains(@class, "item__value")]//text()').string(multiple=True)
    product.category = 'Robot Vacuums'
    product.manufacturer = data.xpath('//tr[contains(@class, "attribute_Manufacturer")]/td[contains(@class, "item__value")]//text()').string(multiple=True)

    product.url = data.xpath('//a[regexp:test(@href, "https://www.amazon.com/dp|https://goto.walmart.com/c")]/@href').string()
    if not product.url:
        product.url = context['url']

    mpn = data.xpath('//span[@class="sku"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//tr[contains(@class, "attribute_Global Trade Identification Number")]/td[contains(@class, "item__value")]//text()').string(multiple=True)
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    review = Review()
    review.type = 'pro'
    review.title = context['name']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//div[@class="ei_last_updated"]/text()').string()
    if date:
        review.date = date.replace('Last updated on ', '').replace(' am', '').replace(' pm', '').strip().rsplit(' ', 1)[0].strip()

    grade_overall = data.xpath('//div[contains(@class, "score_10")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    excerpt = data.xpath('//div[regexp:test(@class, "tabletext|short-description")]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

    revs = data.xpath('//ol[@class="commentlist"]/li')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['url']

        date = rev.xpath('.//time/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//strong[contains(@class, "review__author")]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//span[contains(., "★") and contains(@class, "active")])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        excerpt = rev.xpath('.//div[@class="description"]/p//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            ssid = rev.xpath('@id').string()
            if ssid:
                review.ssid = ssid.split('-')[-1]
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
