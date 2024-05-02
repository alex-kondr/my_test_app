from agent import *
from models.products import *
import simplejson
import httplib


httplib._MAXHEADERS = 1000


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.but.fr/Api/Rest/V1/CMS/Menu'), process_catlist, dict())


def process_catlist(data, context, session):
    cats_json = simplejson.loads(data.content)
    cats = cats_json.get('menuItems', {}).get('values', [])
    for cat in cats:
        name = cat[1]

        sub_cats = cat[7]
        for sub_cat in sub_cats:
            sub_name = sub_cat[0]
            url = 'https://www.but.fr' + sub_cat[3]

            if sub_name != name:
                cat = name +'|' + sub_name
            else:
                cat = name

            session.queue(Request(url), process_subcatlist, dict(cat=cat))


def process_subcatlist(data, context, session):
    cats = data.xpath('//div[@class="category-carousel"]')
    for cat in cats:
        name = cat.xpath('.//h3//text()').string(multiple=True)

        if name not in context['cat']:
            context['cat'] = context['cat'] + '|' + name

        sub_cats = cat.xpath('.//li[@class="splide__slide"]//a')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = sub_cat.xpath('@href').string().split('.html')[0] + '/NW-6272-avis-clients~1~etoile(s)/NW-6272-avis-clients~2~etoile(s)/NW-6272-avis-clients~3~etoile(s)/NW-6272-avis-clients~4~etoile(s)/NW-6272-avis-clients~5~etoile(s)'

            if sub_name not in context['cat']:
                context['cat'] = context['cat'] + '|' + sub_name

            session.queue(Request(url), process_prodlist, dict(cat=context['cat']))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product"]')
    for prod in prods:
        url = prod.xpath('.//a/@href').string()

        rating = prod.xpath('.//div[contains(@class, "infos-rating")]//text()').string()
        if rating:
            session.queue(Request(url), process_product, dict(context, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = data.xpath('//meta[@property="og:title"]/@content').string()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '')
    product.category = context['cat']
    product.manufacturer = data.xpath('//li[contains(., "Marque")]/span[@class]/text()').string()

    ean = data.xpath('//li[contains(., "EAN")]/span[@class]/text()').string()
    if ean and ean.isdigit() and len(ean) > 11:
        product.add_property(type='id.ean', value=ean)

        url = 'https://www.but.fr/Api/Rest/Catalog/Products/{ean}/Reviews.json?PageSize=All'.format(ean=ean)
        session.queue(Request(url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    revs = revs_json.get('items', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('date')
        if date:
            review.date = date.split()[0]

        author = rev.get('pseudo')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rate')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.get('title')
        excerpt = rev.get('content')
        if excerpt and len(excerpt.strip()) > 1:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.replace('???', '').replace('??', '').strip()

            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = rev.get('reviewID')
                if not review.ssid:
                    review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
