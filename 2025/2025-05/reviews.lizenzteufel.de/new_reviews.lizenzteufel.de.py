from agent import *
from models.products import *


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.lizenzteufel.de/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="navigation-flyout"]//a[@class="nav-link"]')
    for cat in cats:
        name = cat.xpath('@title').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name, cat_url=url))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="product-info"]')
    for prod in  prods:
        name = prod.xpath('.//a[@class="product-name"]/text()').string()
        url = prod.xpath('.//a[@class="product-name"]/@href').string()

        rating = prod.xpath('.//div[@class="product-review-rating"]')
        if rating:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, url=url, name=name))

    next_page = data.xpath('//input[@id="p-next" and not(@disabled)]/@value').string()
    if next_page:
        next_url = context['cat_url'] + '?p=' + next_page
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1]
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//input[@name="brand-name"]/@value').string()

    mpn = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 11:
        product.add_property(type='id.ean', value=ean)

    context['product'] = product
    process_reviews(data, context, session)


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url

        date = rev.xpath('.//meta[@itemprop="datePublished"]/@content').string()
        if date:
            review.date = date.rsplit(' ', 1)[0]

        author = rev.xpath('.//div[@itemprop="author"]/meta[@itemprop="name"]/@content').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//div[@class="product-review-point"])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.xpath('.//div[contains(@class, "item-title")]/p[@class]/text()').string()
        excerpt = rev.xpath('.//p[contains(@class, "item-content")]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
