from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://jyllands-posten.dk/kultur/film/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[div[h3[contains(@class, "[overflow-wrap:anywhere]")]]]')
    for rev in revs:
        url = rev.xpath('div[h3]/a/@href').string()
        grade_overall = rev.xpath('count(.//svg[contains(@class, "rating-star-active")])')
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(url=url, grade_overall=grade_overall))

    # no next page


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('//h1[contains(@class, "article")]/text()').string()
    product.url = context['url']
    product.ssid = product.url.split('/')[-3].replace('ECE', '')
    product.category = 'Film'

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.ssid = product.ssid
    review.url = product.url

    date = data.xpath('//time/@datetime[contains(., "T")]').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[span[contains(., "Film- og serieanmelder")]]/span[not(contains(., "Film- og serieanmelder"))]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = context['grade_overall']
    if grade_overall:
        review.grades.append(Grade(type="overall", value=float(grade_overall), best=6.0))

    summary = data.xpath('//div[h1[contains(@class, "article")]]/p[contains(@class, "article-body")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@id="main-content"]/p[not(contains(@class, "article-body"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
