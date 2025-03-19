from agent import *
from models.products import *
import simplejson
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.vg247.com/archive/reviews'), process_revlist, {})


def process_revlist(data, context, session):
    revs = data.xpath('//ul[@class="summary_list"]/li')
    for rev in revs:
        title = rev.xpath('.//p[@class="title"]/a/text()').string()
        url = rev.xpath('.//p[@class="title"]/a/@href').string()
        date = rev.xpath('.//time/@datetime').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url, date=date))

    next_url = data.xpath('//a[span[@aria-label="Next page"]]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    name = data.xpath('//div[contains(@class, "tagged_with_item--primary")][last()]//p/a/text()').string() or context['title']
    product.name = name.split(' Review: ')[0]
    product.url = data.xpath('//li[strong[contains(., "Link")]]/a/@href').string() or context['url']
    product.category = 'Games'

    platform = data.xpath('//*[self::li or self::p][strong[contains(., "Version reviewed")]]/text()').string()
    if platform:
        product.category += '|' + platform

    product.ssid = context['url'].split('/')[-1]

    manufacturer = data.xpath('//li[strong[contains(., "Developer")]]/text()').string() or data.xpath('''//script[contains(., '"productPublishers":')]/text()''').string()
    if manufacturer:
        product.manufacturer = manufacturer.split('"productPublishers": "')[-1].split('",')[0].split(',')[0].replace('-', ' ').capitalize()

    review = Review()
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = context.get('date', '').split('T')[0]

    author = data.xpath('//span[@class="author"]/a').first()
    if author:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()
        if author_name and author_url:
            author_ssid = author_url.split('/')[-1]
            review.authors.append(Person(name=author_name, url=author_url, ssid=author_ssid))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

    grade_overall = data.xpath('//div[@class="review_rating"]/@data-value').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    conclusion = data.xpath('//p[strong[contains(., "Conclusion")]]/text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[regexp:test(., "verdict", "i")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        conclusion = re.sub(r'<[^>]*>', '', conclusion)
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    summary = data.xpath('//p[@class="strapline"]/text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@class="article_body_content"]/p[not(contains(., "This article first appeared on USgamer,") or contains(., "Primary Reviewer,"))][not(preceding::*[contains(@class, "conclusion") or regexp:test(., "verdict", "i")])]//text()').string(multiple=True)
    if excerpt:
        excerpt = re.sub(r'<[^>]*>', '', excerpt)

        review.properties.append(ReviewProperty(type='excerpt', value=excerpt.strip()))

        product.reviews.append(review)

        session.emit(product)
