from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.arlt.com/index.php?cl=topmenu', use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[contains(@class, "navlevel-1")]')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        sub_cats = cat.xpath('ul/li[contains(@class, "navlevel-2")]/a[@class="root"]')
        if sub_cats:
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_subcatlist, dict(context, cat=name + '|' + sub_name))
        else:
            url = cat.xpath('a/@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(context, cat=name))


def process_subcatlist(data, context, session):
    cats = data.xpath('//li[@class="navlevel-3"]/a[@class="root"]')
    if cats:
        for cat in cats:
            name = cat.xpath('text()').string()
            url = cat.xpath('@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(context, cat=context['cat'] + '|' + name))
    else:
        process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    prods = data.xpath('//li[@class="productLine line"]')
    for prod in prods:
        name = prod.xpath('.//a[@class="productTitle"]/text()').string()
        url = prod.xpath('.//a[@class="productTitle"]/@href').string().split('?')[0]

        revs = prod.xpath('.//meter[@class="rating"]')
        if revs:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//meta[@itemprop="sku"]/@content').string()
    product.sku = product.ssid
    product.category = context['cat']

    manufacturer = data.xpath('//div[contains(., "Marke:")]/text()[normalize-space()]').string()
    if manufacturer:
        product.manufacturer = manufacturer.split(':')[-1].strip()

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

        excerpt = rev.xpath('div[@itemprop="description"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
