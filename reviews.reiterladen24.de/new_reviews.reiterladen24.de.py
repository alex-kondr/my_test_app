# from agent import *
# from models.products import *


XCAT = ['Geschenkideen',  'Neuheiten', 'Sale']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.reiterladen24.de/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[div[@class="row navigation-flyout-bar"]]')
    for cat in cats:
        name = cat.xpath('.//a[@class="nav-link"]/@title').string()

        if name not in XCAT:
            sub_cats = cat.xpath('.//div[contains(@class, "is-level-0")]/div')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('.//a[contains(@class, "is-level-0")]/span/text()').string()

                sub_cats1 = sub_cat.xpath('.//div[contains(@class, "is-level-1")]/div')
                if sub_cats1:
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('.//a[contains(@class, "is-level-1")]/span/text()').string()
                        url = sub_cat1.xpath('.//a[contains(@class, "is-level-1")]/@href').string()
                        session.queue(Request(url + '?order=bewertung-desc', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1, prods_url=url))
                else:
                    url = sub_cat.xpath('.//a[contains(@class, "is-level-0")]/@href').string()
                    session.queue(Request(url + '?order=bewertung-desc', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name, prods_url=url))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="card-body"]')
    for prod in prods:
        name = prod.xpath('.//a[@class="product-name"]/text()').string()
        url = prod.xpath('.//a[@class="product-name"]/@href').string()

        revs = prod.xpath('.//p[contains(@class, "product-review-rating-alt-text")]')
        if revs:
            session.queue(Request(url, force_charset='utf-8'), process_product, dict(context, name=name, url=url))
        else:
            return

    next_page = data.xpath('//li[contains(@class, "page-next")]/input/@value').string()
    if next_page:
        next_url = context['prods_url'] + '?order=bewertung-desc&p=' + next_page
        session.queue(Request(next_url, force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="productId"]/@value').string()
    product.sku = data.xpath('//span[@itemprop="sku"]/text()').string()
    product.manufacturer = data.xpath('//meta[@property="product:brand"]/@content').string()
    product.category = context['cat']

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

    revs_url = data.xpath('//form[contains(@class, "review-pagination")]/@action').string()
    next_page = data.xpath('//input[@id="p-next"]/@value').string()
    if revs_url and next_page:
        revs_url = 'https://www.reiterladen24.de' + revs_url
        options = """--compressed -X POST --data-binary $'------geckoformboundary44e5a63219abbf74145442b00025c85e\r\nContent-Disposition: form-data; name="p"\r\n\r\n{}\r\n------geckoformboundary44e5a63219abbf74145442b00025c85e--\r\n'""".format(next_page)
        session.do(Request(revs_url, use='curl', options=options, force_charset='utf-8'), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
