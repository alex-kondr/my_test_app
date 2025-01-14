from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.dolce-gusto.es/capsulas', force_charset='utf-8'), process_catlist, dict(cat='Capsulas'))
    session.queue(Request('https://www.dolce-gusto.es/cafeteras', force_charset='utf-8'), process_catlist, dict(cat='Cafeteras'))
    session.queue(Request('https://www.dolce-gusto.es/accesorios', force_charset='utf-8'), process_catlist, dict(cat='Accesorios'))


def process_catlist(data, context, session):
    sub_cats = data.xpath('//div[contains(@class, "subcategories")]/a[not(contains(., "TODAS"))]')
    if not sub_cats:
        process_prodlist(data, context, session)
        return

    for sub_cat in sub_cats:
        name = sub_cat.xpath('text()').string()
        url = sub_cat.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + name.capitalize()))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-card"]')
    for prod in prods:
        name = prod.xpath('.//a[contains(@class, "product-card__name")]/text()').string()
        url = prod.xpath('.//a[contains(@class, "product-card__name")]/@href').string()

        revs_cnt = prod.xpath('.//div[@class="reviews__actions"]/a/text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            url = 'https://www.dolce-gusto.es/' + url.split('/')[-1]
            session.queue(Request(url, force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    # no next page


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//form/@data-product-sku').string()
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = 'Dolce Gusto'

    revs_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
    if not revs_json:
        return

    revs = simplejson.loads(revs_json).get('review', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

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
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # no next page