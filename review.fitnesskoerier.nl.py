import simplejson

from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.fitnesskoerier.nl'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats1 = data.xpath('//li[@class="item sub use_mega"]')
    for cat1 in cats1:
        name1 = cat1.xpath('a//text()').string()
        
        cats2 = cat1.xpath('.//div[@class="col flex flex-column"]')
        for cat2 in cats2:
            name2 = cat2.xpath('.//a[@class="title"]//text()').string()
        
            cats3 = cat2.xpath('.//a[@class="subtitle"]')
            for cat3 in cats3:
                name3 = cat3.xpath('text()').string()
                url = cat3.xpath('@href').string()
                session.queue(Request(url), process_category, dict(cat=name1+"|"+name2+"|"+name3))


def process_category(data, context, session):
    prods = data.xpath('//div[@class="item is_grid with-sec-image"]')
    for prod in prods:
        name = prod.xpath('.//a[@class="m-img greyed"]/@title').string()
        url = prod.xpath('.//a[@class="m-img greyed"]/@href').string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))

    next_url = data.xpath('//a[@title="Volgende pagina"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_category, dict(context))


def process_product(data, context, session):
    prod_json = simplejson.loads(data.xpath('//script[@type="application/ld+json"]//text()').string().replace('\\', ''))

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = prod_json[2].get('Brand', {}).get('name')
    product.ssid = prod_json[2].get('productID')

    ean = prod_json[2].get('gtin13')
    if ean:
        product.add_property(type='id.ean', value=ean)
        
    mpn = prod_json[2].get('mpn')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    sku = prod_json[2].get('sku')
    if sku:
        product.sku = sku

    revs_count = prod_json[2].get('aggregateRating', {}).get('reviewCount')
    if revs_count and int(revs_count) > 0:
        revs = prod_json[2].get('review', {})
        
        for rev in revs:
            review = Review()
            review.type = "user"
            review.url = product.url
            review.date = rev.get('datePublished')

            author = rev.get('author', {}).get('name').split('[')[0]
            if author:
                review.authors.append(Person(name=author, ssid=author))

            pros_cons = rev.get('author', {}).get('name', '').split('[')
            if len(pros_cons) > 1:
                pros_cons = pros_cons[1].replace('&quot;', '').replace('[', '').replace(']', '').replace('{', '').replace('}', '').split(',')
                for pro_con in pros_cons:
                    if 'plus' in pro_con:
                        review.add_property(type='pros', value=pro_con.split(':')[1])
                    elif 'minus' in pro_con:
                        review.add_property(type='cons', value=pro_con.split(':')[1])
                        
            grade_overall = rev.get('reviewRating', {}).get('ratingValue')
            if grade_overall and grade_overall > 0:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

            excerpt = rev.get('description')
            if excerpt:
                review.add_property(type='excerpt', value=excerpt.replace(' <br />', ''))
                review.ssid = review.digest() if author else review.digest(excerpt)
                product.reviews.append(review)

        if product.reviews:
            session.emit(product)
            