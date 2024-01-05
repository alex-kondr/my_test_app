from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://jyllands-posten.dk/kultur/film/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[h3[contains(@class, "[overflow-wrap:anywhere]")]]')
    for rev in revs:
        url = rev.xpath('a/@href').string()
        title = rev.xpath('h3//text()').string(multiple=True)
        grade_overall = rev.xpath('count(.//svg[contains(@class, "rating-star-active")])')
        session.queue(Request(url), process_review, dict(url=url, title=title, grade_overall=grade_overall))

    #no next page


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.ssid = context['url'].split('/')[-3].replace('ECE', '')
    product.category = 'Film'
    product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.ssid = product.ssid
    review.url = product.url

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split()[0]

    author = data.xpath('//span[@class="c-article-top-byline__name"]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = context['grade_overall']
    if grade_overall:
        review.grades.append(Grade(type="overall", value=float(grade_overall), best=6.0))

    summary = data.xpath('//p[@class="c-article-top-info__description"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@class="c-article-text-container"]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
