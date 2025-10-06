from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.vg-reloaded.com/category/articles/'), process_revlist, {})


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, {})


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(': ', 1)[-1].strip()
    product.url = context['url']
    product.ssid = data.xpath('//article[contains(@class, "type-post")]/@id').string().split('-')[-1]
    product.category = 'Games'

    platform = context['title'].split(' Review')[0].replace('X/S', 'X\\S').strip()
    if platform:
        product.category += '|' + platform

    review = Review()
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.type = "pro"

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "meta-author")]/a/text()').string()
    author_url = data.xpath('//span[contains(@class, "meta-author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade = data.xpath('//h1[regexp:test(., "score:", "i")]//text()').string(multiple=True)
    if not grade:
        grade = data.xpath('//div[contains(@class, "entry-content")]/p[regexp:test(., "score:", "i")]/text()').string()

    if grade:
        grade = grade.split(':')[-1].split('/')[0].strip()
        if grade[0].isdigit():
            review.grades.append(Grade(type="overall", value=float(grade), best=10.0))

    summary = data.xpath('//div[contains(@class, "entry-content")]/p[1]/strong//text()').string(multiple=True)
    if summary:
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath('//div[contains(@class, "entry-content")]/p[preceding-sibling::p[regexp:test(., "the verdict", "i")]]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(regexp:test(., "the verdict", "i"))]//text()').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
