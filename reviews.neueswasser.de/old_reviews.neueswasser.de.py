from agent import *
from models.products import *
import simplejson


XCAT = ['Service']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.neueswasser.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats1 = data.xpath('//ul[contains(@class, "mainmenu ")]/li')
    for cat1 in cats1:
        name1 = cat1.xpath('a/text()').string()

        if name1 not in XCAT:
            cats2 = cat1.xpath('ul/li//a')
            for cat2 in cats2:
                name2 = cat2.xpath('text()').string()
                url = cat2.xpath('@href').string()
                session.queue(Request(url + '?items=1000'), process_prodlist, dict(cat=name1+'|'+name2))


def process_prodlist(data, context, session):
    prods = data.xpath('//ul[contains(@class, "product-list")]/li/div[contains(@class, "item")]/a')
    for prod in prods:
        name = prod.xpath('span/text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    prod_json = data.xpath('''//script[contains(., '"Product"')]/text()''').string().replace('\\', '')
    prod_json = simplejson.loads(prod_json)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = prod_json.get('manufacturer', {}).get('name')
    product.ssid = data.xpath('//single-item/@__item-id').string()
    product.sku = data.xpath('//p[contains(., "Artikelnummer")]/span/text()').string()

    revs_cnt = data.xpath('//div[@data-feedback]/feedback-container/@__options').string()
    if revs_cnt:
        revs_cnt = simplejson.loads(revs_cnt).get('numberOfFeedbacks')
        if revs_cnt and int(revs_cnt) > 0:
            revs_url = 'https://www.neueswasser.de/rest/feedbacks/feedback/helper/feedbacklist/{}/1?feedbacksPerPage=10000'.format(product.ssid)
            session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    revs = revs_json.get('feedbacks', [])
    for rev in revs:
        review = Review()
        review.title = rev.get('title')
        review.type = 'user'
        review.url = product.url

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('authorName')
        if not author:
            author = rev.get('sourceRelation', [{}])[0].get('sourceRelationLabel')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('feedbackRating', {}).get('rating', {}).get('ratingValue')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        excerpt = rev.get('feedbackComment', {}).get('comment', {}).get('message')
        if excerpt:
            excerpt = excerpt.replace('\n', ' ').strip()

            review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # No next page
