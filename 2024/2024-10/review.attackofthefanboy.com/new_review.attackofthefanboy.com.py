from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://attackofthefanboy.com/category/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[contains(@class, "wp-block-gamurs-article-tile__link") and string-length(normalize-space(.)) > 1]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    title = data.xpath('//h1[contains(@class, "content--title")]//text()').string(multiple=True)

    product = Product()
    product.name = title.replace('Review: ', '').replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = 'Games'

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "wp-block-gamurs-author-bio__name")]/text()').string()
    author_url = data.xpath('//a[contains(@class, "wp-block-gamurs-author-bio__name")]/@href').string()
    if author and author_url:
        author_url = author_url.strip('+')
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count(//div[contains(@class, "review-summary__star-rating")]//span[contains(@class, "star-filled")])')
    if grade_overall:
        grade_half = data.xpath('count(//div[contains(@class, "review-summary__star-rating")]//span[contains(@class, "star-half")])')
        if grade_half:
            grade_overall += grade_half / 2

        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//div[contains(@class, "__pros-wrapper")]//li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "__cons-wrapper")]//li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "content--subtitle")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h3|//h2)[regexp:test(., "verdict", "i")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[regexp:test(@class, "review-summary__text$")]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h3|//h2)[regexp:test(., "verdict", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "article-content")]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
