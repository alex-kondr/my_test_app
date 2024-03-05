from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('http://www.gameforfun.com.br/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="jet-listing-dynamic-link__link"]')
    for rev in revs:
        title = rev.xpath('span/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.name = context['title'].replace('Review:', '').split(':')[0].replace('Review', '').replace('review', '').strip()
    product.category = 'Techik'

    review = Review()
    review.type = 'pro'
    review.url = product.url
    review.ssid = product.ssid
    review.title = context['title']

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//h2[@class="elementor-heading-title elementor-size-default"]/a/text()').string()
    author_url = data.xpath('//h2[@class="elementor-heading-title elementor-size-default"]/a/@href').string()
    if author and author_url:
        author = author.split(':')[-1].strip()
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        author = author.split(':')[-1].strip()
        review.authors.append(Person(name=author, ssid=author))

    grades_value = []
    grades = data.xpath('//div[span[@class="elementor-title"]]')
    for grade in grades:
        grade_name = grade.xpath('span[@class="elementor-title"]/text()').string()
        grade_value = float(grade.xpath('.//span[@class="elementor-progress-text"]/text()').string().replace('Pts', ''))
        grades_value.append(grade_value)
        review.grades.append(Grade(name=grade_name, value=grade_value, best=100.0))

    if grades_value:
        grade_overall = round(sum(grades_value) / len(grades_value), 0)
        review.grades.append(Grade(type='overall', value=grade_overall, best=100.0))

    conclusion = data.xpath('//div[@data-id="6c44601"]//p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="elementor-widget-container"]//p//text()').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
