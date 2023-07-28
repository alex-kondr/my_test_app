import simplejson

from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request("https://hrej.cz/reviews"), process_revlist, dict())


def process_revlist(data, context, session):
    prods = data.xpath('//a[@class="un-card-headline"]')
    for prod in prods:
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_review, dict(url=url))

    next_url = data.xpath('//a[@data-datalayer-event-onclick="page_next" and @class="un-chip"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    prod_json = data.xpath('//script[@type="application/ld+json" and contains(text(), "Review")]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

    product = Product()

    name = data.xpath('//span[@class="un-list-item__before" and a[@href="https://hrej.cz/"]]/a[not(contains(@href, "article"))][not(i)]/text()').string()
    if 'Recenze' in name:
        name = data.xpath('//meta[@property="og:title"]/@content').string()
    product.name = name

    product.ssid = context["url"].split('/')[-1]
    product.url = context["url"]
    product.category = "Games"

    manufacturer = prod_json.get('itemReviewed', {})
    if isinstance(manufacturer, dict):
        product.manufacturer = manufacturer.get('publisher')

    review = Review()
    review.title = data.xpath('//meta[@property="og:title"]/@content').string()
    review.ssid = product.ssid
    review.type = "pro"
    review.url = product.url

    date = data.xpath('//div[@class="post-header-info__content post-header-info__content--with-profile"]//span[not(@class)]/text()').string()
    if date:
        review.date = ''.join(date.split(' ')[:3])

    authors = data.xpath('//p[@class="post-header-info__name"]//a')
    for author in authors:
        name = author.xpath('text()').string()
        url = author.xpath('@href').string()
        review.authors.append(Person(name=name, profile_url=url, ssid=url.split('/')[-1]))

    grade_overall = data.xpath("//div[contains(@class,'review-rating')]/@data-rating").string()
    if grade_overall:
        review.grades.append(Grade(type="overall", value=float(grade_overall)/10, best=10.0))

    summary = data.xpath("//div[@class='post-body__perex']/p//text()").string()
    if summary:
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath("//div[@class='review-box__verdict']//p//text()").string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    pros = data.xpath('//div[contains(@class, "review-box__proscons-pros")]//span[@class="un-list-item__text-secondary"]/text()').strings()
    if pros:
        review.properties.append(ReviewProperty(type="pros", value=pros))

    cons = data.xpath('//div[contains(@class, "review-box__proscons-cons")]//span[@class="un-list-item__text-secondary"]/text()').strings()
    if cons:
        review.properties.append(ReviewProperty(type="cons", value=cons))

    excerpt = data.xpath("//div[@class='post-body']/p//text()").string(multiple=True)

    next_page = data.xpath('//a[span[text()="Další" or text()="Poslední"] and not(@disabled="disabled")]/@href').string()
    if next_page:
        review.add_property(type='pages', value=dict(title=review.title + ' - page 1', url=data.response_url))
        session.do(Request(next_page), process_review_next, dict(page=1, product=product, review=review, excerpt=excerpt))
    elif excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_next(data, context, session):
    product = context['product']
    review = context['review']

    page = context['page'] + 1
    review.add_property(type='pages', value=dict(title=review.title + ' - page ' + str(page), url=data.response_url))

    excerpt = context["excerpt"]

    grade_overall = data.xpath("//div[contains(@class,'review-rating')]/@data-rating").string()
    if grade_overall:
        review.grades.append(Grade(type="overall", value=float(grade_overall)/10, best=10.0))

    conclusion = data.xpath("//div[@class='review-box__verdict']//p//text()").string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    pros = data.xpath('//div[contains(@class, "review-box__proscons-pros")]//span[@class="un-list-item__text-secondary"]/text()').strings()
    if pros:
        review.properties.append(ReviewProperty(type="pros", value=pros))

    cons = data.xpath('//div[contains(@class, "review-box__proscons-cons")]//span[@class="un-list-item__text-secondary"]/text()').strings()
    if cons:
        review.properties.append(ReviewProperty(type="cons", value=cons))

    excerpt_next = data.xpath("//div[@class='post-body']/p//text()").string(multiple=True)
    if excerpt_next:
        excerpt += ' ' + excerpt_next

    next_page = data.xpath('//a[span[text()="Další" or text()="Posledni"] and not(@disabled="disabled")]/@href').string()
    if next_page:
        session.do(Request(next_page), process_review_next, dict(page=page, product=product, review=review, excerpt=excerpt))
    elif excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)