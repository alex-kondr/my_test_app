from agent import *
from models.products import *


XCAT = ['Home', 'Special Offers', 'Contact']


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
    session.queue(Request("https://www.clearchemist.co.uk/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(@class, "level0")]')
    for cat in cats:
        name = cat.xpath('a/span/text()').string()

        if name not in XCAT:
            subcats = cat.xpath('.//li[contains(@class, "level1")]/a')
            if subcats:
                for subcat in subcats:
                    subcat_name = subcat.xpath('.//text()').string(multiple=True)
                    url = subcat.xpath('@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name+'|'+subcat_name))
            else:
                url = cat.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//li[contains(@class, "item product")]')
    for prod in prods:
        name = prod.xpath('.//a[@class="product-item-link"]/text()').string()
        url = prod.xpath('.//a[@class="product-item-link"]/@href').string()
        ssid = prod.xpath('.//div/@data-product-id').string()
        sku = prod.xpath('.//form/@data-product-sku').string()

        revs_cnt = prod.xpath('.//a[@class="action view"]/text()').string()
        if revs_cnt and int(revs_cnt) > 0:
            revs_url = "https://www.clearchemist.co.uk/review/product/listAjax/id/{}/".format(ssid)
            session.queue(Request(revs_url), process_product, dict(context, name=name, url=url, ssid=ssid, sku=sku))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat'].replace('Shop|', '').strip(' |')
    product.ssid = context['ssid']

    sku = context.get('sku')
    if sku and sku.isdigit() and len(sku) > 10:
        product.add_property(type='id.ean', value=sku)
    else:
        product.sku = sku

    context['product'] = product
    process_reviews(data, context, session)


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath("//li[@class='item review-item']")
    for rev in revs:
        review = Review()
        review.url = product.url
        review.type = 'user'
        review.date = rev.xpath('.//time/@datetime').string()

        author = rev.xpath('.//strong[@itemprop="author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@itemprop="ratingValue"]/text()').string()
        if grade_overall:
            grade_overall = float(grade_overall.strip("%")) / 20
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.xpath('div[@class="review-title"]/text()').string()
        excerpt = rev.xpath(".//div[@class='review-content']//text()").string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    next_url = data.xpath('//a[@class="action  next"]/@href').string()
    if next_url:
        session.do(Request(next_url), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
