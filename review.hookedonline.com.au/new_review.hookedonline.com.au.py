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
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request("https://www.hookedonline.com.au/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(@class, "Products")]//ul[@class="level_1"]/li')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        cats1 = cat.xpath('.//ul[contains(@class, "first-col")]/li')
        for cat1 in cats1:
            cat1_name = cat1.xpath('a/text()').string()

            subcats = cat1.xpath('ul/li/a')
            if subcats:
                for subcat in subcats:
                    subcat_name = subcat.xpath('text()').string()
                    url = subcat.xpath('@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
            else:
                url = cat1.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "card-body")]')
    for prod in prods:
        name = prod.xpath('.//p[contains(@class, "title")]/a/text()').string()
        mpn = prod.xpath('.//meta[@itemprop="mpn"]/@content').string()
        url = prod.xpath('.//p[contains(@class, "title")]/a/@href').string()

        rating = prod.xpath('.//span[@itemprop="ratingCount"]')
        if rating:
            session.queue(Request(url), process_product, dict(context, name=name, mpn=mpn, url=url))

    next_url = data.xpath('//a[i[contains(@class, "fa-chevron-right")]]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat'].replace('|Other Boating', '')
    product.manufacturer = data.xpath('//div[@class="product_brads_logo"]//@title').string()

    mpn = context['mpn']
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    sku = data.xpath('//meta[@itemprop="sku"]/@content').string()
    if sku != mpn:
        product.sku = sku

    revs = data.xpath('//div[@aria-labelledby="tabReviews"]//div[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//strong/comment()').string()
        if date:
            review.date = date.split('">')[-1].rsplit(' ', 1).strip()

        author = rev.xpath('.//span[@itemprop="author"]//text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//meta[@itemprop="ratingValue"]/@content').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//span[@itemprop="description"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
