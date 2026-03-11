from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('http://www.wheelsforwomen.ie/index.php/category/car-seat-review/', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//div[@class='et-description']/h2/a")
    for rev in revs:
        title = rev.xpath(".//text()").string()
        url = rev.xpath("@href").string()

        if 'Review: ' in title:
            session.queue(Request(url, max_age=0), process_product, dict(title=title, url=url))

    next_url = data.xpath("//link[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_revlist, dict())


def process_product(data, context, session):
    product = Product()
    product.name = context['title'].split("Review: ")[-1].strip()
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2].replace('review-', '')
    product.category = 'Car Seat Review'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath("//meta[@property='article:published_time']/@content").string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="author"]/@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//p[strong[contains(., "Why you’ll want one")]]/text()').string(multiple=True)
    if pros:
        review.add_property(type='pros', value=pros)

    cons = data.xpath('//p[strong[contains(., "Why you won’t")]]/text()').string()
    if cons:
        review.add_property(type='cons', value=cons)

    grade_overall = data.xpath('//p[strong[contains(., "Star Rating")]]/text()[contains(., "* (")]').string()
    if grade_overall:
        grade_overall = grade_overall.split('*')[0].split(':')[-1]
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    summary = data.xpath('//meta[@property="og:description"]/@content').string()
    if summary and not '[…]' in summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//p[position() > 1 and position() < last()][not(contains(., "Where can I buy one"))][not(contains(., "Why you’ll want one"))][not(strong[contains(., "Why you won’t")])][following-sibling::p[strong[contains(., "Seat:")]]]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="left-area"]/p[not(contains(@class, "comment"))][not(strong[text()="{}"])]//text()').string(multiple=True).format(author)

    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '')

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
