from agent import *
from models.products import *


XCAT = ['Gifts and Seasonal Items']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.cremashop.eu/en/categories/', use="curl", force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@id="shop-categories"]/div')
    for cat in cats:
        name = cat.xpath('h3//text()').string(multiple=True)

        if name not in XCAT:
            sub_cats = cat.xpath('.//ul[@class="widget-list"]/li')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a/text()').string()

                if not sub_name.startswith('All '):
                    sub_cats1 = sub_cat.xpath('ul//a')
                    if sub_cats1:
                        for sub_cat1 in sub_cats1:
                            sub_name1 = sub_cat1.xpath('text()').string()
                            url = sub_cat1.xpath('@href').string()
                            session.queue(Request(url + '?sort=rating', use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                    else:
                        url = sub_cat.xpath('a/@href').string()
                        session.queue(Request(url + '?sort=rating', use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-card")]')
    for prod in prods:
        name = prod.xpath('.//h4/a/text()').string()
        url = prod.xpath('.//h4/a/@href').string()

        rating = prod.xpath('.//div[@class="star-rating"]')
        if rating:
            session.queue(Request(url, use="curl", force_charset='utf-8'), process_product, dict(context, name=name, url=url))
        else:
            return

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next, use="curl", force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//li[contains(., "Brand")]/a/text()').string()

    prod_json = data.xpath('''//script[contains(., '"@type":"Product"') and contains(., '"mpn":"')]/text()''').string()
    if prod_json:
        mpn = prod_json.split('"mpn":"')[-1].split('","')[0].strip(' "')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//li[contains(., "EAN")]/span/text()').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[@data-review]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@data-review').string()
        review.date = rev.xpath(".//time/@datetime").string()

        author = rev.xpath("span/text()").string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade = rev.xpath("@data-rating").string()
        if float(grade) > 0:
            review.grades.append(Grade(type='overall', value=float(grade), best=5.0))

        title = rev.xpath(".//h5/text()").string()
        excerpt = rev.xpath("p//text()").string(multiple=True)
        if excerpt and len(excerpt) > 1:
            review.title = title
        else:
            excerpt = title

        if excerpt and len(excerpt) > 1:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
