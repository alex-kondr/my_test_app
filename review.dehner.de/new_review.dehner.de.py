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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.dehner.de/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[@data-level="1"]')
    for cat in cats:
        name = cat.xpath('a//span[contains(@class, "container--title")]/text()').string()

        sub_cats = cat.xpath('ul[contains(@class, "menu")]/li[.//span]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('a//span[contains(@class, "container--title")]/text()').string()

            sub_cats1 = sub_cat.xpath('ul[contains(@class, "menu")]/li[.//span]')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('a//span[contains(@class, "container--title")]/text()').string()
                url = sub_cat1.xpath('a/@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "product-item") and h5]/a')
    for prod in prods:
        name = prod.xpath('h5/text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('=')[-1]
    product.sku = product.ssid
    product.category = context['cat']

    manufacturer = data.xpath('//img[contains(@class, "product-logo")]/@src').string()
    if manufacturer:
        product.manufacturer = manufacturer.split('/')[-1].title()

    revs = data.xpath('//article[@class="review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//span[@itemprop="datePublished"]/text()').string()
        if date:
            review.date = date.rsplit(' ', 1)[0]

        author = rev.xpath('.//span[@itemprop="author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//input[@name="rating"]/@value').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.xpath('.//div[@itemprop="name"]/text()').string()
        excerpt = rev.xpath('.//div[@itemprop="reviewBody"]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt and len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
