from agent import  *
from models.products import *
import simplejson


XCAT = ['Easter Deals', 'SALE %', 'Marken', 'Geschenke', 'Blog']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.fundis-reitsport.de/'), process_fronpage, dict())


def process_fronpage(data, context, session):
    cats = data.xpath('//ul[contains(@class, "is--level0") and li/ul]/li')
    for cat in cats:
        name = cat.xpath('a/span[@class="navigation--link-label"]//text()').string(multiple=True)

        if name not in XCAT:
            sub_cats = cat.xpath('ul/li[contains(@class, "navigation--entry")] ')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a//text()').string(multiple=True)

                if 'Alle' not in sub_name:
                    sub_cats1 = sub_cat.xpath('ul/li[contains(@class, "navigation--entry")] ')
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('a//text()').string(multiple=True)
                        url = sub_cat1.xpath('a/@href').string()

                        if 'Alle' not in sub_name1:
                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                    else:
                        url = sub_cat.xpath('.//a[contains(., "Alle")]/@href ').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))
            else:
                url = sub_cat.xpath('.//a[contains(., "Alle")]/@href ').string()
                session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="fundis-product-box-name"]/a[@class="product--title"]')
    for prod in prods:
        name = prod.xpath('text()[normalize-space()]').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//meta[@itemprop="productID"]/@content').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[@class="product--supplier"]//img/@alt').string()
    product.sku = data.xpath('//span[@itemprop="sku"]/text()').string()

    mpn = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//tr[contains(., "EAN")]/td[@class="product--properties-value"]/text()').string()
    if ean and ean.isdigit() and len(ean) > 12:
        product.add_property(type='id.ean', value=ean)

    revs_cnt = data.xpath('//meta[@itemprop="ratingCount"]/@content').string()
    if revs_cnt and int(revs_cnt) > 0:
        revs_url = 'https://apps.fundis-reitsport.de/api/trusted-shops/ratings'
        options = '''-X POST -H 'Content-Type: application/json' --data-raw '{"id":"''' + product.sku + '","shopId":1}\''
        session.do(Request(revs_url, use='curl', options=options), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    revs = revs_json.get('target_shop', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('date')
        if date:
            review.date = date.split('T')[0]

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        author = rev.get('customerName')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        excerpt = rev.get('comment', {}).get('german')
        if excerpt and len(excerpt) > 1:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = rev.get('id')
            if not review.ssid:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

#no next page
