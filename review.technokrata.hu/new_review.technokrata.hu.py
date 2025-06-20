from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.technokrata.hu/tesztek/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "main-blog-text") and h2]')
    for rev in revs:
        title = rev.xpath('h2/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Teszt:', '').strip()
    product.url = context['url']
    product.category = data.xpath('//h3[contains(@class, "post-cat")]//text()').string() or 'Technika'

    ssid = data.xpath('//div[regexp:test(@class, "post-\d+")]/@class').string()
    if ssid:
        product.ssid = ssid.split()[0].split('-')[-1]
    else:
        product.ssid = product.url.split('/')[-2]

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    summary = data.xpath('//span[contains(@class, "post-excerpt")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Összességében")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(., "Verdict")]/following-sibling::p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Összességében")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(., "Verdict")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
