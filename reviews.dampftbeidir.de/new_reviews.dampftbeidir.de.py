from agent import *
from models.products import *


XCATS = ['Marken', 'Sale', 'NEU']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.dampftbeidir.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@data-menu-sort]')
    for cat in cats:
        name = cat.xpath('.//a[contains(@class, "kk-fm-entry-label")]/span/text()').string()

        if name not in XCATS:
            sub_cats = data.xpath('.//div[@class="kk-fm-listing--item-wrapper" or contains(@class, "kk-fm-listing--linklist-level0")]')
            if sub_cats:
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath('(span|.//a)/text()').string()
                    url = sub_cat.xpath('(.//a|preceding-sibling::a[contains(@class, "kk-fm-link")][1])/@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))
            else:
                url = cat.xpath('.//a[@class="kk-fm-entry-label kk-fm-link"]/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//a[@class="text-clamp-2"]')
    for prod in  prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1]
    product.category = context['cat']
    product.sku = data.xpath('//span[@itemprop="sku"]/text()').string()
    product.manufacturer = data.xpath('//span[contains(text(), "Hersteller:")]//span[@itemprop="name"]/text()').string()

    context['product'] = product
    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//body/div[@class="col"]')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.title = rev.xpath('.//span[@class="subheadline"]/text()').string()
        review.date = rev.xpath('following::head[1]/meta[@itemprop="datePublished"]/@content').string()

        author = rev.xpath('.//span[@itemprop="name"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('preceding::body[1]//span[@itemprop="ratingValue"]/text()').string()
        if grade_overall and grade_overall > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.xpath('following::body[1]//span[@class="verified-purchase"]/text()').string()
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.xpath('.//small[@class="d-none"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
