import simplejson

from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.tires-easy.com/tire-categories'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="single-category"]')
    for cat in cats:
        name = cat.xpath('div[@class="single-category-title"]/p/text()').string()
        subcats = cat.xpath('.//li/a')
        url = cat.xpath('.//a[@class="all-subcat-link"]/@href').string()

        if subcats:
            for subcat in subcats:
                subname = subcat.xpath('text()').string()
                url = subcat.xpath('@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + subname))
        else:
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="productListItem"]')
    for prod in prods:
        name = prod.xpath('.//h2/a/text()').string()
        url = prod.xpath('.//h2/a/@href').string()
        sku = prod.xpath('.//select[@name="qty"]/@productcode').string()
        manufacturer = prod.xpath('.//select[@name="qty"]/@data-gtm-product-brand').string()

        revs_cnt = prod.xpath('.//input[@class="rating-count"]/@value').string()
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url, sku=sku, manufacturer=manufacturer))

    next_url = data.xpath('//li[@class="next"]/a/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1]
    product.category = context['cat']
    product.sku = context['sku']
    product.manufacturer = context['manufacturer']

    product_info = data.xpath('//div[@class="main-content row"]/script/text()').string()
    if product_info:
        mpn = product_info.split('mpn: "')[-1].split('",')[0]
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = product_info.split('gtin: "')[-1].split('",')[0]
        if ean:
            product.add_property(type='id.ean', value=ean)

    revs_url = 'https://www.resellerratings.com//product_ratings/ui/reviews.json?product_id=' + product.sku + '&merchant_id=1037&limit=1000'
    session.queue(Request(revs_url), process_review, dict(product=product))


def process_review(data, context, session):
    revs_json = simplejson.loads(data.content)
    new_data = data.parse_fragment(revs_json['ratings_html'])

    product = context['product']

    revs = new_data.xpath('//div[@class="grid-x grid-container"]')
    for rev in revs:
        if product.name.lower() not in rev.xpath('.//div[@class="rr-heavy-txt rr-product-variant-name"]/text()').string().lower():
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.title = rev.xpath('.//div[@class="acs_review_title"]/text()').string()
        review.date = rev.xpath('.//span[@class="acs_reviewer_stats_value"]/text()').string()

        verified = rev.xpath('.//div[@class="acs_verified_user rr-button"]/text()').string()
        if verified:
            review.add_property(type='is_verified_buyer', value=True)

        recommend = rev.xpath('.//div[@class="acs_review_recommend rr-heavy-txt acs_review_recommend_bottom acs_js_hide_on_filter"]/text()').string(multiple=True)
        if recommend:
            review.properties.append(ReviewProperty(type='is_recommended', value=True))

        helpful = rev.xpath('.//div[@class="acs_review_helpful"]/text()').string()
        if helpful:
            helpful_total = int(helpful.split('of ')[-1].split(' found')[0])
            if helpful_total > 0:
                helpful_votes = int(helpful.split(' of')[0])
                review.add_property(type='helpful_votes', value=helpful_votes)

                review.add_property(type='not_helpful_votes', value=helpful_total-helpful_votes)

        grade_overall = rev.xpath('count(.//div[@data-ratingtype="stars"]//span[contains(@class, "acs_blox_fill_100")])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        author = rev.xpath('.//div[@class="acs_reviewer_name"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        excerpt = rev.xpath('.//div[@class="acs_review_text acs_js_review_attribute"]/text()').string()
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest()

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
