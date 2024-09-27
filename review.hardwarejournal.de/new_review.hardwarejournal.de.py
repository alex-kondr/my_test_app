from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.hardwarejournal.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@class="sub-menu"]/li/a[@class="menu-link"]')
    for cat in cats:
        name = cat.xpath('span[@class="menu-text"]/text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "post-content")]')
    for rev in revs:
        title = rev.xpath('.//a[@rel="bookmark"]/text()').string()
        url = rev.xpath('.//a[@rel="bookmark"]/@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(': ')[0]
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    rev_json = data.xpath('//script[@type="application/ld+json"]//text()').string()
    if rev_json:
        rev_json = simplejson.loads(rev_json)[-1]

        date = rev_json.get('datePublished')
        if date:
            review.date = date.split('T')[0]

        author = rev_json.get('author', {}).get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//p[span[contains(@id, "more")]]/preceding-sibling::p//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//div[contains(@class, "entry-content")]/p[1]//text()').string(multiple=True)

    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath("//h3[contains(.,'Fazit')]/following-sibling::p//text()").string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(.,"Fazit")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(contains(., "Beschichtung:") or contains(., "Model:"))]//text()').string(multiple=True)

    if excerpt:

        if summary:
            excerpt = excerpt.replace(summary, "").strip()
        if conclusion:
            excerpt = excerpt.replace(conclusion, "").strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
