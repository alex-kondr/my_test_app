from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.hardwarejournal.de/kat/tests', use="curl"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "post-content")]')
    for rev in revs:
        title = rev.xpath('h2[@class="entry-title"]/a/text()').string()
        url = rev.xpath('h2[@class="entry-title"]/a/@href').string()
        summary = rev.xpath('div[contains(@class, "entry-content")]/p/text()').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url, summary=summary))

    next_url = data.xpath('//a[contains(@class, "next page")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(': ')[0]
    product.ssid = context['url'].split('.de/')[-1].strip('/')
    product.url = context['url']

    category = ''
    cats = data.xpath('//li[@class="trail-item"]')
    for cat in cats:
        cat_name = cat.xpath('.//text()').string()
        if cat_name:
            category += cat_name + '|'
    if category:
        product.category = category.strip('|')

    review = Review()
    review.title = context['title']
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']

    # date = data.xpath('//meta[@property="og:updated_time"]/@content').string() ——— doesn't work for a few reviews
    date = data.xpath('//script[@type="application/ld+json"]//text()').string()
    if date:
        review.date = date.split('datePublished":"')[-1].split('T')[0]

    conclusion = data.xpath("//h3[contains(.,'Fazit')]/following-sibling::p//text()").string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    summary = context.get('summary')
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))

    excerpt = data.xpath('//div[contains(@class, "entry-content")]/p//text()').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, "")
        if conclusion:
            excerpt = excerpt.replace(conclusion, "")

        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

        product.reviews.append(review)
        session.emit(product)
