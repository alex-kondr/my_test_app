from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.tires-easy.com/tire-categories'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="categories__single"]')
    for cat in cats:
        name = cat.xpath('div[@class="categories__single-title"]/p/text()').string()

        sub_cats = cat.xpath('div[@class="categories__single-inner"]//li/a')
        if sub_cats:
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = cat.xpath('@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))
        else:
            url = cat.xpath('.//div[@class="all-subcat-link"]/a/@href').string()
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="plp-list__item-container"]')
    for prod in prods:
        name = prod.xpath('.//h2/a/text()').string()
        url = prod.xpath('.//h2/a/@href').string()

        revs_cnt = prod.xpath('.//div[contains(@class, "reviews")]/a/text()').string()
        if revs_cnt:
            revs_cnt = int(revs_cnt.split()[0])
            if revs_cnt > 0:
                session.queue(Request(url), process_product, dict(context, name=name, url=url, revs_cnt=revs_cnt))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.sku = data.xpath('//div/@data-product').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//div/@data-gtm-product-brand').string()

    mpn = data.xpath('//input[@class="product-sku"]/@value').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//script[contains(., "gtin:")]').string()
    if ean:
        ean = ean.split('gtin: "')[-1].split('",')[0]
        if ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_url = 'https://www.resellerratings.com//product_ratings/ui/reviews.json?product_id=' + product.sku + '&merchant_id=1037&limit=5'
    session.queue(Request(revs_url), process_review, dict(context, product=product))


def process_review(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    new_data = data.parse_fragment(revs_json['ratings_html'])

    revs = new_data.xpath('//div[@class="grid-x grid-container"]')
    for rev in revs:
        if product.name.lower() not in rev.xpath('.//div[@class="rr-heavy-txt rr-product-variant-name"]/text()').string().lower():
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.title = rev.xpath('.//div[@class="acs_review_title"]/text()').string()
        review.date = rev.xpath('.//span[@class="acs_reviewer_stats_value"]/text()').string()

        author = rev.xpath('.//div[@class="acs_reviewer_name"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//div[@data-ratingtype="stars"]//span[contains(@class, "acs_blox_fill_100")])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        is_verified = rev.xpath('.//div[@class="acs_verified_user rr-button"]/text()').string()
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        is_recommended = rev.xpath('.//div[@class="acs_review_recommend rr-heavy-txt acs_review_recommend_bottom acs_js_hide_on_filter"]/text()').string(multiple=True)
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        helpful = rev.xpath('.//div[@class="acs_review_helpful"]/text()').string()
        if helpful:
            helpful_total = int(helpful.split('of ')[-1].split(' found')[0])
            if helpful_total > 0:
                helpful_votes = int(helpful.split(' of')[0])
                review.add_property(type='helpful_votes', value=helpful_votes)

                review.add_property(type='not_helpful_votes', value=helpful_total-helpful_votes)

        excerpt = rev.xpath('.//div[@class="acs_review_text acs_js_review_attribute"]/text()').string()
        if excerpt:
            excerpt = excerpt.strip(' .+-"')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        next_url = 'https://www.resellerratings.com//product_ratings/ui/reviews.json?product_id=' + product.sku + '&merchant_id=1037&limit=5&offset=' + str(offset)
        session.queue(Request(next_url), process_review, dict(context, product=product, offset=offset))

    elif product.reviews:
        session.emit(product)
