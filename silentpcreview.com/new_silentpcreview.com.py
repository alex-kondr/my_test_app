from agent import *
from models.products import *
import re


XCAT = ['About Us', 'Benchmarks', 'Do-It-Yourself Systems', 'Donations|Giveaways', 'How To', 'Internet News', "MikeC's Audio Craft", 'News', 'Popular Guides', 'Reference|Recommended', 'Silent PC Build Guides', 'Site News', 'The Silent Front', 'Uncategorized']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://silentpcreview.com/categories/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//h3/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="elementor-widget-container" and .//h3 and a]')
    if not revs:
        revs = data.xpath('//h3/a')

    for rev in revs:
        title = rev.xpath('.//h3/text()').string() or rev.xpath('text()').string()
        url = rev.xpath('a/@href').string() or rev.xpath('@href').string()

        if title and not re.search(r'Save \d+%|^Best ', title):
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']
    product.manufacturer = data.xpath('//tr[contains(., "Manufacturer")]//b[not(contains(., "Manufacturer"))]/text()').string()

    product.name = data.xpath('//tr[contains(., "Product")]//b[not(contains(., "Product"))]/text()').string()
    if not product.name:
        product.name = context['title'].replace('', '').strip()

    mpn = data.xpath('//tr[contains(., "Model")]//b[not(contains(., "Model"))]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content|//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//li[@itemprop="author"]//span[contains(@class, "author")]/text()').string(multiple=True)
    author_url = data.xpath('//li[@itemprop="author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//p[span[contains(@id, "more-")]]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[contains(., "FINAL THOUGHTS")]/following-sibling::p[not(@align)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[contains(., "FINAL THOUGHTS")]/preceding-sibling::p[not(@align)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body/p[not(@align)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
