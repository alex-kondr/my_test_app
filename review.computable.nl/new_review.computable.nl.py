from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.computable.nl/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//li[contains(., "Thema’s")]/ul//a')
    for cat in cats:
        name = cat.xpath('.//text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('(//h3|//h2)[@class="entry-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "entry-author-name")]/text()').string()
    author_url = data.xpath('//a[contains(@class, "entry-author-name")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('(//div[@class="entry-content"]/p)[1]/strong//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@class="entry-content"]/p[not(@class)]//text()').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
