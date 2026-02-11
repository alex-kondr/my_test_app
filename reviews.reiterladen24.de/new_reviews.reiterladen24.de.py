from agent import *
from models.products import *


XCAT = ['Geschenkideen',  'Neuheiten', 'Sale']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.reiterladen24.de/', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[div[@class="row navigation-flyout-content"]]')
    for cat in cats:
        name = cat.xpath('.//a[@itemprop="url" and not(@class)]/@title').string()

        if name not in XCAT:
            cats1 = cat.xpath('.//div[contains(@class, "is-level-0")]/div')
            for cat1 in cats1:
                cat1_name = cat1.xpath('.//a[contains(@class, "is-level-0")]/span/text()').string()

                subcats = cat1.xpath('.//div[contains(@class, "is-level-1")]/div')
                if subcats:
                    for subcat in subcats:
                        subcat_name = subcat.xpath('.//a[contains(@class, "is-level-1")]/span/text()').string()
                        url = subcat.xpath('.//a[contains(@class, "is-level-1")]/@href').string()
                        session.queue(Request(url + '?order=bewertung-desc', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name, prods_url=url))
                else:
                    url = cat1.xpath('.//a[contains(@class, "is-level-0")]/@href').string()
                    session.queue(Request(url + '?order=bewertung-desc', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name + '|' + cat1_name, prods_url=url))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="card-body"]')
    for prod in prods:
        name = prod.xpath('.//a[@class="product-name"]/text()').string()
        url = prod.xpath('.//a[@class="product-name"]/@href').string()

        revs = prod.xpath('.//p[contains(@class, "product-review-rating-alt-text")]')
        if revs:
            session.queue(Request(url, force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url))
        else:
            return

    next_page = data.xpath('//li[contains(@class, "page-next")]/a/@data-page').string()
    if next_page:
        next_url = context['prods_url'] + '?order=bewertung-desc&p=' + next_page
        session.queue(Request(next_url, force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//meta[@itemprop="productID"]/@content').string()
    product.sku = data.xpath('//span[@itemprop="sku"]/text()').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[@property="product:brand"]/@content').string()

    mpn = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    context['product'] = product

    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//body[div[@class="row product-detail-review-item-info"]]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//div[contains(@class, "date")]//small/text()').string()
        if date:
            review.date = date.rsplit(' ', 1)[0].strip()

        grade_overall = rev.xpath('.//p[contains(@class, "rating")]/text()').string()
        if grade_overall:
            grade_overall = grade_overall.split('Bewertung mit')[-1].split('von')[0].replace(',', '.').strip()
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.xpath('.//div[contains(@class, "verify")]/text()')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.xpath('.//p[@class="h5"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[contains(@class, "content")]//text()').string(multiple=True)
        if excerpt and len(excerpt.strip(' .+-*')) > 2:
            if title:
                review.title = title.strip(' .+-*')
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.strip(' .+-*')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest(excerpt)

                product.reviews.append(review)

    next_url = data.xpath('//li[contains(@class, "page-next")]/a/@href').string()
    if next_url:
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
