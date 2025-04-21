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
    session.queue(Request('https://www.arlt.com/index.php?cl=topmenu'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats1 = data.xpath('//li[@class="navlevel-0  "][a[contains(., "Produkte")]]//li[@class="navlevel-1   "]')
    for cat1 in cats1:
        name1 = cat1.xpath('a[@class="root  "]/text()').string().strip()
        url = cat1.xpath('a[@class="root  "]/@href').string()

        cats2 = cat1.xpath('ul[@class="navlevel-2"]/li')
        if not cats2:
            session.queue(Request(url), process_prodlist, dict(cat=name1))

        for cat2 in cats2:
            name2 = cat2.xpath('a[@class="root  "]/text()').string().strip()
            url = cat2.xpath('a[@class="root  "]/@href').string()

            cats3 = cat2.xpath('ul[@class="navlevel-3"]/li/a[@class="root  "]')
            if not cats3:
                session.queue(Request(url), process_prodlist, dict(cat=name1+'|'+name2))

            for cat3 in cats3:
                name3 = cat3.xpath('text()').string().strip()
                url = cat3.xpath('@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name1+'|'+name2+'|'+name3))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//li[@class="productLine line"]')
    for prod in prods:
        name = prod.xpath('.//a[@class="productTitle"]/text()').string()
        url = prod.xpath('.//a[@class="productTitle"]/@href').string().split('?')[0]

        is_reviewed = prod.xpath('.//div[@class="rating"]/meter')
        if is_reviewed:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat'].replace('Apple', '').replace('Microsoft', '').replace("Samsung", '').replace("mehr...", '').strip('| ')
    product.manufacturer = data.xpath('//div[@itemprop="brand"]/meta/@content').string()
    product.ssid = data.xpath('//meta[@itemprop="sku"]/@content').string()
    product.sku = product.ssid

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//time[@itemprop="datePublished"]/@datetime').string()

        author = rev.xpath('.//span[@itemprop="author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@itemprop="ratingValue"]/text()').string()
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('div[@itemprop="description"]/text()').string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)