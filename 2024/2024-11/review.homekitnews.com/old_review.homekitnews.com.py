from agent import *
from models.products import *
import re


XCAT = ['apple', 'aqara', 'eve', 'mi', 'mijia', 'hpm', 'reviews', 'lifesmart', 'd-link', 'vocolinc', 'youtube', 'ikea', 'velux', 'wozart', 'opus', 'ge', 'athom', 'philips', 'zemismart']


def run(context, session):
    session.queue(Request('https://homekitnews.com/category/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="cm-post-content"]')
    for rev in revs:
        title = rev.xpath('.//h2[contains(@class, "title")]/a/text()').string()
        url = rev.xpath('.//h2[contains(@class, "title")]/a/@href').string()
        date = rev.xpath('.//time[contains(@class, "published")]/@datetime').string()
        session.queue(Request(url), process_review, dict(title=title, url=url, date=date))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('//h2[@class="cwp-item"]/text()').string() or context['title'].split(' (review')[0]
    product.url = data.xpath('//div[contains(@class, "affiliate-button")]/a/@href').string() or context['url']
    product.ssid = context['url'].split('/')[-2]

    category = ''
    cats = data.xpath('//a[@rel="category tag"]/text()').strings()
    for cat in cats:
        if cat.lower() not in XCAT:
            category += cat + '|'

    product.category = category.replace('/', ' ').strip(' |') if category else 'Tech'

    review = Review()
    review.title = context['title']
    review.url = context['url']
    review.type = 'pro'
    review.ssid = product.ssid

    date = context.get('date')
    if date:
        review.date = date.split("T")[0]

    author = data.xpath('//span[contains(@class, "author")]/a').first()
    if author:
        author_name = author.xpath("text()").string()
        author_url = author.xpath("@href").string()     # url with all revs by author
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author_name, ssid=author_ssid))

    grade_overall = data.xpath('//div[contains(@class, "grade-content")]//span/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//div[@class="rev-option"]')
    for grade in grades:
        name = grade.xpath('div/h3//text()').string()
        value = grade.xpath('div/span/text()').string(multiple=True)
        if value:
            value = value.split('/')[0]
            review.grades.append(Grade(name=name, value=float(value), best=10.0))

    pros = data.xpath('//div[@class="pros"]/ul/li/text()').strings()
    for pro in pros:
        if pro:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="cons"]/ul/li/text()').strings()
    for con in cons:
        if con:
            review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[contains(@class, "entry-summary")]//p[preceding-sibling::p[regexp:test(., "conclusion:", "i") or regexp:test(., "in conclusion", "i" or contains(., "CONCLUSION"))]]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "entry-summary")]//p[contains(., "CONCLUSION")]/text()').string()
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    excerpt = data.xpath('//div[contains(@class, "entry-summary")]//p[not(preceding-sibling::p[regexp:test(., "conclusion:", "i") or contains(., "CONCLUSION") or regexp:test(., "in conclusion", "i")])][not(regexp:test(., "conclusion:", "i") or contains(., "CONCLUSION") or regexp:test(., "in conclusion", "i"))]//text()').string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

        product.reviews.append(review)

        session.emit(product)
