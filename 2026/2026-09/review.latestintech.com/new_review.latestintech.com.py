from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://latestintech.com/category/reviews/'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//h2[contains(@class, "gb-headline-text")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].split(' Review')[0].strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = 'Tech'

    product.url = data.xpath('//a[@rel="noreferrer noopener" or @data-type="link"]/@href').string()
    if not product.url:
        product.url = context['url']

    tags = data.xpath('//meta[@property="article:tag"]/@content').strings()
    for tag in tags:
        if data.xpath('//a[regexp:test(@href, "{tag}", "i") and contains(@href, "/tag/")]/text()'.format(tag=tag.replace(' ', '-'))):
            product.category = tag
        elif not product.manufacturer:
            product.manufacturer = tag

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    summary = data.xpath('//div[h1]/p[contains(@class, "headline-tex")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "conclusion|summary", "i")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "conclusion|summary", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-content")]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)