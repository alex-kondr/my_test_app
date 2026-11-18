from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://jyllands-posten.dk/kultur/film/'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[article]/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(url=url))

    # no next page


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = data.xpath('//h1/text()').string()
    product.url = context['url']
    product.ssid = product.url.split('/')[-3].replace('ECE', '')
    product.category = 'Film'

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.ssid = product.ssid
    review.url = product.url

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[span[contains(., "Film- og serieanmelder")]]/span[not(contains(., "Film- og serieanmelder"))]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count(//svg[contains(@class, "fill-grey-50")])')
    if grade_overall and float(grade_overall) > 0:
        review.grades.append(Grade(type="overall", value=float(grade_overall), best=6.0))

    summary = data.xpath('//p[contains(@class, "container-article")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@id="main-content"]/p[not(contains(@class, "container-article"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)