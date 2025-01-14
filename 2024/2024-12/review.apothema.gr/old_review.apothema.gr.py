from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.apothema.gr/afygranthres'), process_category, dict(context, cat_url='https://www.apothema.gr/afygranthres', cat_name="Αφυγραντήρες"))
    session.queue(Request('https://www.apothema.gr/klimatistika'), process_category, dict(context, cat_url='https://www.apothema.gr/klimatistika', cat_name="Κλιματιστικά"))
    session.queue(Request('https://www.apothema.gr/aksesouar-klimatismou-afygrantiron'), process_category, dict(context, cat_url='https://www.apothema.gr/aksesouar-klimatismou-afygrantiron', cat_name="Αξεσουάρ Κλιματισμού"))
    session.queue(Request('https://www.apothema.gr/ionistes-katharistes'), process_category, dict(context, cat_url='https://www.apothema.gr/ionistes-katharistes', cat_name="Ιονιστές & Καθαριστές"))
    session.queue(Request('https://www.apothema.gr/ygranthres'), process_category, dict(context, cat_url='https://www.apothema.gr/ygranthres', cat_name="Υγραντήρες"))
    # Bug of the website - category not available
    session.queue(Request('https://www.apothema.gr/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//ul[@class='nav navbar-nav']/li[@class='dropdown']/a[@class='dropdown-toggle megamenu-desktop']")
    for cat in cats:
        title = cat.xpath(".//text()").string()
        frontcat_url = cat.xpath("@href").string()
        session.queue(Request(frontcat_url), process_category, dict(context, frontcat_url=frontcat_url, title=title))


def process_category(data, context, session):
    prods = data.xpath("//div[@class='product__item product_in_category']/div[@class='product__caption']/span[@class='product__title']")
    if prods:
        process_productlist(data, context, session)

    cats = data.xpath("//div//h2/a[@class='popular__title']")
    for cat in cats:
        cat_name = cat.xpath(".//text()").string()
        cat_url = cat.xpath("@href").string()
        session.queue(Request(cat_url), process_category, dict(context, cat_url=cat_url, cat_name=cat_name))


def process_productlist(data, context, session):
    prods = data.xpath("//div[@class='product__item product_in_category']/div[@class='product__caption']/span/a")
    for prod in prods:
        prod_name = prod.xpath('.//text()').string(multiple=True)
        prod_url = prod.xpath('@href').string()
        session.queue(Request(prod_url), process_product, dict(context, prod_url=prod_url, prod_name=prod_name))

    next_url = data.xpath("//ul[@class='pagination pull-right']/li/a[@aria-label='Next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_productlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['prod_name']
    product.url = context['prod_url']
    product.category = context['cat_name']
    product.manufacturer = data.xpath("//ul[@class='product__specs']/li[contains(.,'Κατασκευαστής')]/a/text()").string()
    product.ssid = context['prod_url'].split('/')[-1]
    product.sku = data.xpath("//p[@class='product__contact-code']/strong/text()").string()

    ean = data.xpath("//ul[@class='product__specs']/li[contains(.,'Κωδ. Κατασκευαστή')]/text()").string()
    if ean:
        product.properties.append(ProductProperty(type='id.ean', value=ean.split(' ')[-1]))

    revs = data.xpath("//div[@id='reviews']//div[@class='reviews__panel thumbnail']")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['prod_url']
        review.title = rev.xpath(".//h3[@class='review__item__title']/text()").string(multiple=True)

        date = rev.xpath(".//p[@class='review__item__info']/text()").string(multiple=True)
        if date:
            review.date = date.split(' ')[1]

        author = rev.xpath(".//p[@class='review__item__info']/strong/text()").string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade = rev.xpath(".//div[@class='reviews__rating']//div[@class='reviews__rating__total']/text()").string(multiple=True)
        if grade:
            review.grades.append(Grade(name='overall', value=float(grade), best=5.0))

        excerpt = rev.xpath(".//p[@class='review__item__text']/text()").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            review.ssid = '%s-%s' % (product.ssid, hashlib.md5(author + excerpt).hexdigest())
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
