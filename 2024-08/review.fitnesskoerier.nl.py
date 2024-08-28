from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.fitnesskoerier.nl'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[@class="item sub use_mega"]')
    for cat in cats:
        name = cat.xpath('a//text()').string()

        cats1 = cat.xpath('.//div[@class="col flex flex-column"]')
        for cat1 in cats1:
            name1 = cat1.xpath('.//a[@class="title"]//text()').string()
            url = cat1.xpath('.//a[@class="title"]/@href').string()
            session.queue(Request(url), process_prodlist, dict(cat=name+"|"+name1))

            subcats = cat1.xpath('.//a[@class="subtitle"]')
            for subcat in subcats:
                name2 = subcat.xpath('text()').string()
                url = subcat.xpath('@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name+"|"+name1+"|"+name2))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="item is_grid with-sec-image"]')
    for prod in prods:
        name = prod.xpath('.//a[@class="m-img greyed"]/@title').string()
        url = prod.xpath('.//a[@class="m-img greyed"]/@href').string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))

    next_url = data.xpath('//a[@title="Volgende pagina"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    prod_json = data.xpath('//script[@type="application/ld+json"]//text()').string().replace('\\', '').replace('&#039;', "'").replace('<br />', '').replace('&amp;#128170;&amp;#127997;', '').replace('&amp; ', '& ').replace('&amp;#128077;', '').replace('&amp;#128522;', '')
    if prod_json:
        prod_json = simplejson.loads(prod_json)
    else:
        return

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

    revs_count = prod_json[2].get('aggregateRating', {}).get('reviewCount', 0)
    if int(revs_count) == 0:
        return

    revs = prod_json[2].get('review', {})
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.date = rev.get('datePublished')

        author = rev.get('author', {}).get('name')
        if author:
            author = author.split('[')[0]
            review.authors.append(Person(name=author, ssid=author))

        pros_cons = rev.get('author', {}).get('name', '').split('[')
        if len(pros_cons) > 1:
            pros_cons = pros_cons[1].replace('&quot;', '').replace('[', '').replace(']', '').replace('{', '').replace('}', '').split(',')
            for pro_con in pros_cons:
                if 'plus' in pro_con:
                    review.add_property(type='pros', value=pro_con.split(':')[1].strip())
                elif 'minus' in pro_con:
                    review.add_property(type='cons', value=pro_con.split(':')[1].strip())

        grade_overall = rev.get('reviewRating', {}).get('ratingValue')
        if grade_overall and grade_overall > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('description')
        if excerpt:
            excerpt = excerpt.replace('&quot;', "'")

            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
