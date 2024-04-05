from agent import *
from models.products import *
import simplejson


XCAT = ['New arrivals', 'Collections', 'Sale']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://tamaris.com/en-ES/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "dropdown-level-1")]')
    for cat in cats:
        name = cat.xpath('a/span/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('.//ul[contains(@class, "dropdown-level-2")]/li')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('div/span/text()').string()

                if sub_name not in XCAT:
                    sub_cats1 = sub_cat.xpath('.//li[@class="dropdown-item"]')
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('a/span/text()').string()
                        url = sub_cat1.xpath('a/@href').string()

                        if 'All' not in sub_name1:
                            session.queue(Request(url + '?sz=48'), process_prodlist, dict(cat=name + '|' + sub_name1))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@data-ean]')
    for prod in prods:
        name = prod.xpath('.//div[contains(@class, "product-name")]/text()').string()
        ean = prod.xpath('@data-ean').string()
        ssid = prod.xpath('@data-uuid').string()
        mpn = prod.xpath('@data-product-id').string()
        url = prod.xpath('.//a[@class="tile-link"]/@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, ean=ean, ssid=ssid, mpn=mpn, url=url))

    next_url = data.xpath('//a[contains(@class, "load-more-results")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = product.ssid
    product.manufacturer = 'Tamaris'
    product.category = context['cat']

    if context['mpn']:
        product.add_property(type='id.manufacturer', value=context['mpn'])

    if context['ean']:
        product.add_property(type='id.ean', value=context['ean'])

    revs_url = 'https://cdn-ws.turnto.eu/v5/sitedata/7ow2UbXsJQJAP18site/{mpn}/r/relatedReview/en_IE/0/9999/RECENT?'.format(mpn=context['mpn'])
    session.queue(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    revs = revs_json.get('reviews')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.get('dateCreatedFormatted')

        author = rev.get('user', {}).get('firstName', '') + ' ' + rev.get('user', {}).get('lastName', '')
        author_ssid = rev.get('user', {}).get('id')
        if author and author_ssid:
            review.authors.append(Person(name=author.strip(), ssid=author_ssid))
        elif author:
            review.authors.append(Person(name=author.strip(), ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.get('upVotes')
        if hlp_yes and hlp_yes > 0:
            review.add_property(type='helpful_votes', value=hlp_yes)

        hlp_no = rev.get('downVotes')
        if hlp_no and hlp_no > 0:
            review.add_property(type='not_helpful_votes', value=hlp_yes)

        is_recommended = rev.get('recommended')
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        is_verified_buyer = rev.get('purchaseDateFormatted')
        if is_verified_buyer and len(is_verified_buyer) > 2:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('title')
        excerpt = rev.get('text')
        if excerpt and len(excerpt) > 1:
            review.title = title
        else:
            excerpt = title

        if excerpt and len(excerpt) > 1:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = rev.get('id')
            if not review.ssid:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    revs_cnt = revs_json.get('total')
    if int(revs_cnt) > len(revs):
        raise ValueError('!!!!!!!!', product.url)

    if product.reviews:
        session.emit(product)