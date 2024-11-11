from agent import *
from models.products import *


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.rockpapershotgun.com/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//p[@class="title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[span[@aria-label="Next page"]]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' review: ')[0].split(' Review: ')[0].split(' Review In ')[0].replace('Review In Progress:', '').replace('Wot I Think:', '').replace(' review', '').replace(' Review', '').replace('Verdict: ', '').strip()
    product.ssid = context['url'].split('/')[-1].replace('-review', '')
    product.category = 'Games'

    product.manufacturer = data.xpath('//li[contains(., "Developer:")]/text()').string()
    if not product.manufacturer:
        product.manufacturer = data.xpath('//strong[contains(., "Developer:")]/following-sibling::text()[1]').string()

    product.url = data.xpath('//li[contains(., "From:")]/a/@href').string()
    if not product.url:
        product.url = data.xpath('//strong[contains(., "From:")]/following-sibling::a[1]/@href').string()
    if not product.url:
        product.url = context['url']

    platform = data.xpath('//li[contains(., "On:")]/text()').string()
    if platform:
        product.category += '|' + platform.replace(', ', '/')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="author"]/a/text()').string()
    author_url = data.xpath('//span[@class="author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//p[@class="strapline"]//text()').string(multiple=True)
    if summary:
        summary = summary.replace('Verdict:', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[contains(@class, "article_body_content")]/aside/text()[not(preceding-sibling::*[contains(., "Developer:") or contains(., "Publisher:") or contains(., "Release:")])]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "article_body_content")]/p//text()[not(regexp:test(., "href=|targeting cookies|cookie settings"))]').string(multiple=True)
    if excerpt:
        if 'Conclusions?' in excerpt:
            excerpt, conclusion = excerpt.split('Conclusions?')
            review.add_property(type='conclusion', value=conclusion.strip())

        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
