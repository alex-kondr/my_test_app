from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.gamekapocs.hu/cikkek/tesztek', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h1/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//li[@class="right"]/a[contains(@href, "https://www.gamekapocs.hu/cikkek/tesztek")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' teszt')[0].replace('', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = 'Games'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if not date:
        date = data.xpath('//li[@class="lajk"]/text()').string()

    if date:
        review.date = date.split('T')[0].strip(' .')

    author = data.xpath('//li[@class="nick"]/a/text()').string()
    author_url = data.xpath('//li[@class="nick"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[@id="cikk_lead_inner"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@id="articletext"]/p[not(preceding-sibling::div[@class="fb_like"])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
