from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://awservice.gmbh'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@data-widget_type="heading.default" and .//h2/a]')
    for cat in cats:
        name = cat.xpath('.//h2//text()').string(multiple=True)

        sub_cats = cat.xpath('(following-sibling::div[@data-widget_type="nav-menu.default"]//ul)[1]//a')
        if sub_cats:
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string().replace(' / ', '/')
                url = sub_cat.xpath('@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))
        else:
            url = cat.xpath('.//a/@href').string()
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//li[contains(@class, "product type-product")]')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('h2/text()').string()
        product.ssid = prod.xpath('.//@data-sku').string()
        product.sku = product.ssid
        product.url = prod.xpath('a/@href').string()
        product.category = context['cat']

        prod_id = ''.join(['3' + numb for numb in product.sku])
        url = 'https://integrations.etrusted.com/feeds/product-reviews/v1/channels/chl-37a24b53-a99a-4844-8ca3-e01f8c350e84/sku/{prod_id}/default/all/feed.json'.format(prod_id=prod_id)

        session.queue(Request(url), process_reviews, dict(product=product))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_reviews(data, context, session):
    product = context['product']

    revs = simplejson.loads(data.content)
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.ssid = rev.get('id')
        review.url = product.url

        date = rev.get('submittedAt')
        if date:
            review.date = date.split('T')[0]

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('isVerified')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.get('comment')
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
