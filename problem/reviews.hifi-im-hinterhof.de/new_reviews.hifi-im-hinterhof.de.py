from agent import *
from models.products import *


XCAT = ['* RESTPOSTEN *', 'Weitere']


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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.hifi-in-offenbach.de/de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[contains(@class, "level-1")]/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name and name not in XCAT:
            sub_cats = cat.xpath('ul/li/a')

            if sub_cats:
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath('text()').string()
                    url = sub_cat.xpath('@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name+'|'+sub_name))
            else:
                url = cat.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "title")]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    # product.ssid = context['ssid']
    product.manufacturer = data.xpath('//meta[@itemprop="brand"]/@content').string()
    product.sku = data.xpath('//meta[@itemprop="sku"]/@content').string()

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    if data.xpath('//*[contains(@class, "review") or contains(@itemprop, "review") or contains(@id, "review")]'):
        raise ValueError('!!!')

    # revs_cnt = data.xpath('//span[@itemprop="reviewCount"]/text()').string()
    # if revs_cnt and int(revs_cnt) > 0:
    #     revs_url = "https://www.hifi-im-hinterhof.de/review/product/listAjax/id/{}/?limit=50".format(product.ssid)
    #     session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath("//li[@class='item review-item']")
    for rev in revs:
        review = Review()
        review.title = rev.xpath('div[@class="review-title"]/text()').string()
        review.url = product.url
        review.type = 'user'
        review.date = rev.xpath('.//time/@datetime').string()

        author = rev.xpath('.//strong[@itemprop="author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@itemprop="ratingValue"]/text()').string()
        if grade_overall:
            value = float(grade_overall.strip("%")) / 20
            review.grades.append(Grade(type='overall', name='Gesamtbewertung', value=value, best=5.0))

        excerpt = rev.xpath(".//div[@class='review-content']//text()").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # no next page
