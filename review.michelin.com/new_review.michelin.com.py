from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.michelinman.com/auto/browse-tires/all-tires', use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="ds__card-body"]')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('h2//span[contains(@class, "productName")]/text()').string()
        product.url = prod.xpath('a/@href').string()
        product.ssid = product.url.split('/')[-1]
        product.category = 'Car tires'
        product.manufacturer = 'Michelin'

        revs_cnt = prod.xpath('.//span[contains(@class, "rating-stars-count")]')
        if revs_cnt:
            session.queue(Request(product.url + '/reviews', use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))

# no next page


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[contains(@class, "reviews-list")]/div[contains(@class, "review svelte")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//div[contains(@class, "review-info-header__postedon")]/text()').string()
        if date:
            review.date = date.replace('Posted on', '').replace(' by', '').strip()

        author = rev.xpath('.//div[contains(@class, "review-info-header__postedon")]/strong/text()').string()
        if author:
            author = author.replace('Anonymous', '').strip()
            if author:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[contains(@class, "rating-stars-grade")]/text()').string()
        if grade_overall:
            grade_overall = grade_overall.split('/')[0]
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.xpath('.//div[span[contains(text(), "Purchase date:")]]/text()[normalize-space(.)]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        is_recommended = rev.xpath('.//span[contains(text(), "I recommend this tire")]')
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        title = rev.xpath('.//h3[contains(@class, "review-summary-title")]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[contains(@class, "review-summary-description")]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    next_url = data.xpath('//a[contains(@class, "link-next available")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
