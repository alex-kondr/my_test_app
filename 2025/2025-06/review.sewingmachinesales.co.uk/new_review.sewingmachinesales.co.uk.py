from agent import *
from models.products import *


XCAT = ['Specials', 'Outlet']


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
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.sewingmachinesales.co.uk/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[contains(@class, "megamenu")]/li[contains(@class, "level0")]//a')
    for cat in cats:
        name = cat.xpath('.//text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    strip_namespace(data)

    sub_cats = data.xpath('//li[@class="item"]/div[@class="cat-box-text" or contains(@class, "category-name")]//a')
    if sub_cats:
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = sub_cat.xpath('@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_catlist, dict(cat=context['cat'] + '|' + sub_name))
    else:
        process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//li[contains(@class, "product-item")]')
    for prod in prods:
        name = prod.xpath('.//*[contains(@class, "product-item-name")]/a/text()').string()
        ssid = prod.xpath('.//div/@data-product-id').string()
        url = prod.xpath('.//*[contains(@class, "product-item-name")]/a/@href').string()

        revs_cnt = prod.xpath('.//a[@class="action view"]')
        if revs_cnt:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, ssid=ssid, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//td[@data-th="Manufacturer"]/text()').string()

    mpn = data.xpath('//div[@itemprop="sku"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//meta[@itemprop="gtin"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs_url = 'https://www.sewingmachinesales.co.uk/review/product/listAjax/id/{}/'.format(product.ssid)
    session.do(Request(revs_url, use='curl', force_charset='utf-8'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//li[contains(@class, "review-item")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//time/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//strong[@itemprop="author"]/span/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[@class="rating-result"]/@title').string()
        if grade_overall:
            grade_overall = grade_overall.strip(' %')
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

        excerpt = rev.xpath('.//div[@class="review-content"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            ssid = rev.xpath('.//div/@id').string()
            if ssid:
                review.ssid = ssid.replace('review_', '').split('_')[0]
            if not review.ssid:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
