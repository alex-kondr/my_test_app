from agent import *
from models.products import *
import simplejson


XCAT = ['CREA TU CAJA', 'DESCUBRE', 'SUELDO Y PREMIO', 'OFERTAS', 'MÁS', 'RECICLAJE', 'Marcas', 'Servicios', 'FORMATO PROMOCIONAL', 'DESCUBRIR TODAS LAS VARIEDADES']


def run(context, session):
    session.queue(Request('https://www.dolce-gusto.es/', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats1 = data.xpath('//div[@class="menu horizontal"]/ul/li')
    for cat1 in cats1:
        name1 = cat1.xpath('a/text()').string()
        if name1 not in XCAT:
            cats2 = cat1.xpath('ul//li/div[@class="items-container"]//*[self::div or self::figure][@class="item-title"] | ul//li//div[@data-element="inner"]/div[h3]')
            for cat2 in cats2:
                name2 = cat2.xpath('.//h3//span//text()').string()
                if name2 not in XCAT:
                    if name2 == name1:
                        name2 = ''

                    cats3 = cat2.xpath('following-sibling::*')
                    for cat3 in cats3:
                        if cat3.xpath('self::*[@class="item-title"]'):
                            break

                        name3 = cat3.xpath('self::a/@title').string()
                        url = cat3.xpath('self::a/@href').string()
                        if name3 and name3 not in XCAT and url:
                            session.queue(Request(url, max_age=0), process_prodlist, dict(cat=name1+'|'+name2+'|'+name3))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-card"]')
    for prod in prods:
        name = prod.xpath('.//h2[@class="product-card__name"]/a/text()').string()
        ssid = prod.xpath('.//h2[@class="product-card__name"]/a/@href').string().split('/category/')[0].strip('/').split('/')[-1]
        url = 'https://www.dolce-gusto.es/' + ssid

        revs_cnt = prod.xpath('.//div[@class="reviews__actions"]/a/text()').string()
        if revs_cnt:
            revs_cnt = revs_cnt.strip('( )')
            if int(revs_cnt) > 0:
                session.queue(Request(url, max_age=0), process_product, dict(context, name=name, url=url, ssid=ssid))

    # No next page


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.manufacturer = 'Dolce Gusto'
    product.url = context['url']
    product.category = context['cat'].replace('||', '|')
    product.ssid = context['ssid']

    prod_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()

    prod_json = simplejson.loads(prod_json)

    revs = prod_json.get('review', [])
    for rev in revs:
        review = Review()

        review.url = product.url
        review.type = 'user'

        date = rev.get('datePublished')
        if date:
            review.date = date.split()[0]

        author = rev.get('author', {}).get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('reviewRating', {}).get('ratingValue')
        if grade_overall:
            grade_overall = float(grade_overall / 20)
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.get('name')
        excerpt = rev.get('description')
        if excerpt:
            review.title = title.replace('\r', '').replace('\n', ' ')
        elif title:
            excerpt = title

        if excerpt:
            excerpt = excerpt.replace('\r', '').replace('\n', ' ')
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
