from agent import *
from models.products import *
import simplejson


XCAT = ['Kampanjer', 'Gavekort', 'Gjenbruksbutikken', 'Outlet', 'Vis alle']

# Prune gets stuck on these pages and doesn't continue parsing
XPROD = [
    'https://www.multicom.no/pc-produksjon-stromkabel-fra-feks-vegguttak/cat-p/c100874/p10508324'
]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.multicom.no/', use='curl', force_charset='utf-8'), process_frontpage, {})


def process_frontpage(data, context, session):
    cats1 = data.xpath('//ul[contains(@class, "submenu-0")]/li')
    for cat1 in cats1:
        name1 = cat1.xpath('a/span[@class="elipsis"]/text()').string()

        if name1 not in XCAT:
            cats2 = cat1.xpath('ul/li[contains(@class, "submenu-1")]')
            for cat2 in cats2:
                name2 = cat2.xpath('a/span[@class="elipsis"]/text()').string()

                if name2 not in XCAT:
                    cats3 = cat2.xpath('ul/li[contains(@class, "submenu-2")]')

                    if cats3:
                        for cat3 in cats3:
                            name3 = cat3.xpath('a/span[@class="elipsis"]/text()').string()

                            if name3 not in XCAT:
                                cats4 = cat3.xpath('ul/li[contains(@class, "submenu-3")]')

                                if cats4:
                                    for cat4 in cats4:
                                        name4 = cat4.xpath('a/span[@class="elipsis"]/text()').string()
                                        if name4 and name4 not in XCAT:
                                            url = cat4.xpath('a/@href').string()
                                            session.queue(Request(url, use='curl', force_charset='utf-8'), process_category, dict(cat=name1+'|'+name2+'|'+name3+'|'+name4))

                                elif name1 and name2 and name3:
                                    url = cat3.xpath('a/@href').string()
                                    session.queue(Request(url, use='curl', force_charset='utf-8'), process_category, dict(cat=name1+'|'+name2+'|'+name3))

                    elif name1 and name2:
                        url = cat2.xpath('a/@href').string()
                        session.queue(Request(url, use='curl', force_charset='utf-8'), process_category, dict(cat=name1+'|'+name2))


def process_category(data, context, session):
    prods = data.xpath('//a[@data-product-link]')
    for prod in prods:
        name = prod.xpath('text()').string(multiple=True)
        manufacturer = prod.xpath('span/text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, manufacturer=manufacturer, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_category, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('p', '')
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = context['manufacturer']

    mpn = data.xpath('//div/@data-sku').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//div[@class="b-product-sku" and contains(., "EAN")]/div/text()').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    revs_cnt = data.xpath('//div[contains(@class, "rating")]/span/span/text()').string()
    if revs_cnt and int(revs_cnt.split()[0]) > 0:
        revs_url = 'https://widget.trustpilot.com/data/jsonld/business-unit/46db331e00006400050113a8/product?sku={}&numberOfReviews=10&productName=0&templateId=5717796816f630043868e2e8'.format(mpn)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, revs_cnt=int(revs_cnt.split()[0])))


def process_reviews(data, context, session):
    product = context['product']

    try:
        revs = simplejson.loads(data.content).get('productReviews', {}).get('reviews', [])
    except:
        return

    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('consumer', {}).get('displayName')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('stars')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        grades = rev.get('attributes')
        for grade in grades:
            value = float(grades.get(grade))
            review.grades.append(Grade(name=grade, value=value, best=5.0))

        excerpt = rev.get('content')
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = rev.get('id')
            if not review.ssid:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    offset = context.get('offset', 0) + 10
    if offset < context['revs_cnt']:
        raise ValueError('!!!!!')
        revs_url = 'https://widget.trustpilot.com/data/jsonld/business-unit/46db331e00006400050113a8/product?sku={}&numberOfReviews=10&productName=0&templateId=5717796816f630043868e2e8'.format(mpn)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
