from agent import *
from models.products import *

import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.moglix.com/all-categories'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="all-cate-section pad-15"]')
    for cat in cats:
        name = cat.xpath('h3[@class="red-txt"]/text()').string()

        sub_cats = cat.xpath('.//div[@class="cate-type"]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('.//strong[@data-_ngcontent-sc230]/text()').string()

            sub_cats1 = sub_cat.xpath('a[not(strong)]')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('text()').string()
                url = sub_cat1.xpath('@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))

            else:
                url = sub_cat.xpath('a[strong]/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))
        else:
            url = cat.xpath('a/@href').string()
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-vertical-grid-card-container"]')
    for prod in prods:
        name = prod.xpath('.//div[@class="name"]//span/text()').string()
        if name:
            manufacturer = prod.xpath('.//div[contains(@class, "brand")]/span/text()').string().replace('By:', '').strip()
            url = prod.xpath('.//div[@class="name"]/a/@href').string()

            if prod.xpath('.//span[starts-with(@class, "count")]/text()'):
                session.queue(Request(url), process_product, dict(context, name=name, manufacturer=manufacturer, url=url))
        else:
            return

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()

    prod_json = data.xpath('//script[@type="application/ld+json"]/text()[contains(., "sku")]').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)
        product.sku = prod_json['sku']
        product.add_property(type="id.manufacturer", value=prod_json['mpn'])

    product.name = context["name"]
    product.url = context["url"]
    product.ssid = context['url'].split('/')[-1]
    product.category = context["cat"]
    product.manufacturer = context['manufacturer']

    revs_json = data.xpath('//script[@type="application/json"]/text()').string().replace('&q;', '"')
    revs_json = simplejson.loads(revs_json)

    if product.sku:
        revs = revs_json.get('product-review-' + product.sku.lower(), {}).get('data', {}).get('reviewList', {})
    else:
        revs = revs_json.get('product-review-' + product.ssid.split('-')[0], {}).get('data', {}).get('reviewList', {})

    if revs:
        for rev in revs:
            review = Review()
            review.type = 'user'
            review.title = rev['reviewSubject']
            review.ssid = rev['reviewId']
            review.url = product.url

            date = rev.get('createdAt')
            if not date:
                date = rev.get('updatedAt')
            if date:
                review.date = date.split('T')[0]

            grade_overall = rev.get('rating')
            if grade_overall:
                review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

            author = rev.get('userName')
            if author:
                review.authors.append(Person(name=author, ssid=author))

            is_verified = rev.get('isApproved')
            if is_verified:
                review.add_property(type="is_verified_buyer", value=True)

            helpful = rev.get('isReviewHelpfulCountYes')
            if helpful:
                review.add_property(type='helpful_votes', value=helpful)

            not_helpful = rev.get('isReviewHelpfulCountNo')
            if not_helpful:
                review.add_property(type='not_helpful_votes', value=not_helpful)

            excerpt = rev.get('reviewText')
            if excerpt:
                review.add_property(type="excerpt", value=excerpt)

                product.reviews.append(review)

        if product.reviews:
            session.emit(product)
