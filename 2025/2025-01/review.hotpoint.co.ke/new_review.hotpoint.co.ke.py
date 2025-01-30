from agent import *
from models.products import *


XCAT = ['TVs by Brand', 'TVs by Size', 'Audio By Brand', 'Fridges By Brand', 'Size (Width)', 'Commercial']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://hotpoint.co.ke/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "nav-item dropdown header-menu-mega")]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('.//div[@class="header-menu-mega__subcat"]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a//text()').string(multiple=True)

                if sub_name not in XCAT:
                    sub_cats1 = sub_cat.xpath('ul/li/a')
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('text()').string()
                        url = sub_cat1.xpath('@href').string()
                        category = (name + '|' + sub_name + '|' + sub_name1).replace('TVs By Feature|', '')
                        session.queue(Request(url + '?items_per_page=84'), process_prodlist, dict(cat=category))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="card product-card"]')
    for prod in prods:
        url = prod.xpath('a/@href').string()
        session.queue(Request(url), process_product, dict(context, url=url))

    next_url = data.xpath('//a[text()="Next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = data.xpath('//div[@class="product-title"]/h1/text()').string()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].split('_')[-1]
    product.sku = data.xpath('//tr[th[text()="SKU"]]/td/text()').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//p[@class="product-brand"]/a/text()').string()

    mpn = data.xpath('//tr[th[text()="UPC"]]/td/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    session.do(Request(product.url + 'reviews/'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="row" and not(.//h5[contains(., "Average rating")])]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = data.response_url

        date = rev.xpath('.//p[@class="small"]/text()').string(multiple=True)
        if date:
            review.date = date.replace('reviewed on', '').strip()

        author = rev.xpath('.//p[@class="small"]/i/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//ol/@data-count').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.xpath('.//span[contains(., "Verified Purchase")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.xpath('.//h5/a/text()').string()
        excerpt = rev.xpath('div[contains(@class, "col-md-8")]/p//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    next_url = data.xpath('.//a[@class="page-link page-paginator-link" and contains(., "Next")]/@href').string()
    if next_url:
        session.do(Request(next_url), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
