from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://latestintech.com/category/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "gb-headline-text")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' Review')[0]
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2].replace('-review', '')

    product.category = data.xpath("//div[@class='post-tags footer-block-links clearfix']//a[1]//text()").string()
    if not product.category:
        product.category = data.xpath("//div[@class='crumb'][last()]//text()").string(multiple=True)
    if not product.category:
        product.category = 'Tech'

    # cat
    # //meta[@property="article:tag"]/@content
    # //a[regexp:test(@href, //meta[@property="article:tag"]/@content, "i") and contains(@href, "/tag/")]/text()
    
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    grades = data.xpath("//div[@class='lets-review-block__crit']")
    for grade in grades:
        name = grade.xpath(".//div[@class='lets-review-block__crit__title lr-font-h']//text()").string()
        value = grade.xpath(".//div[@class='lets-review-block__crit__score']//text()").string()
        review.grades.append(Grade(name=name, value=float(value), best=10.0))

    grade_overall = data.xpath("//div[@class='score']//text()").string()
    if grade_overall:
        review.grades.append(Grade(type='overall', name='Total Score', value=float(grade_overall), best=10.0))

    conclusion = data.xpath("//div[@class='entry-content body-color clearfix link-color-wrap']/h2[contains(.,'Summary')]/following-sibling::p//text()").string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath("//div[@class='entry-content body-color clearfix link-color-wrap']/h2[contains(.,'Summary')]/preceding-sibling::p//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@class='entry-content body-color clearfix link-color-wrap']//p//text()").string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)
        session.emit(product)
