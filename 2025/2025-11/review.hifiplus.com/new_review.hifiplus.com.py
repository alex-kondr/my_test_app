from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request("https://hifiplus.com/reviews/"), process_revlist, dict())


def process_revlist(data, context, session):
    cats = data.xpath('//div[@class="content-box" or @class="text-box"]/a')
    for cat in cats:
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_review, dict(url=url))

    next_url = data.xpath('//li/a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, {})


def process_review(data, context, session):
    title = data.xpath('//h1/text()').string()

    product = Product()
    product.name = title.replace(' review', '').replace(' Review', '').replace('Review ', '').strip()
    product.url = data.xpath('//a[@data-wpel-link="external"][preceding-sibling::*[contains(., "Manufacturer")] or parent::*[preceding-sibling::*[contains(., "Manufacturer")]]]/@href').string() or context['url']
    product.ssid = context['url'].strip('/').split('/')[-1]
    product.category = 'Tech'

    manufacturer = data.xpath('//*[self::p or self::h3 or self::h4][contains(., "Manufacturer:") or regexp:test(., "Manufactur.* by:", "i")]/text()').string()
    if not manufacturer or not manufacturer.split(':')[-1].strip():
        manufacturer = data.xpath('//*[self::h3 or self::h4][contains(., "Manufacturer")]/following-sibling::p[normalize-space()][1]/text()').string()

    if manufacturer:
            product.manufacturer = manufacturer.split(':')[-1].strip()

    review = Review()
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid
    review.type = 'pro'

    date = data.xpath('''//script[contains(., '"datePublished":"')]/text()''').string()
    if date:
        review.date = date.split('"datePublished":"')[-1].split('T', 1)[0]

    author = data.xpath('//ul[@class="detail-list"]/li/a[contains(@href, "author")]').first()
    if author:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()
        author_ssid = author_url.strip('/').split('/')[-1]
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_ssid))

    conclusion = data.xpath('//div[@class="content-box"]//p[preceding::*[self::h3 or self::h4 or self::b][regexp:test(., "Final Thought|Conclusion", "i")]][normalize-space()][not(preceding::*[regexp:test(., "^\s*Technical specification|Learn more about|\s*Price and Contact Details|Final Thought", "i")])][not(regexp:test(., "^\s*Price and Contact Details|Learn more about", "i"))]//text()').string(multiple=True)
    if conclusion and conclusion.strip():
        review.add_property(type='conclusion', value=conclusion.strip())

    excerpt = data.xpath('//div[@class="content-box"]//p[not(preceding::*[regexp:test(., "^\s*Technical specification|Learn more about|\s*Price and Contact Details|Final Thought|Conclusion", "i")])][not(regexp:test(., "^\s*Price and Contact Details|Learn more about|Conclusion", "i"))]//text()').string(multiple=True)
    if excerpt and excerpt.strip():
        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
