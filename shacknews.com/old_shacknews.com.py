from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.shacknews.com/topic/review', force_charset='utf-8', ), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[@class="article-content-wrapper"]')
    for rev in revs:
        url = rev.xpath('.//a[@class="article-title"]/@href').string()
        title = rev.xpath('.//h3//text()').string(multiple=True)
        datetime = rev.xpath('.//time/@datetime').string()
        author = rev.xpath('.//address/a/text()').string()
        author_url = rev.xpath('.//address/a/@href').string()
        if url:
            session.queue(Request(url), process_review, dict(context, url=url, title=title, datetime=datetime, author=author, author_url=author_url))

    nexturl = data.xpath('//link[@rel="next"]/@href').string()
    if nexturl:
        session.queue(Request(nexturl), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].replace(' Review', '').replace('Mini-Review', '').replace(' Reviews', '').split('review: ')[0].split('review -')[0].split(' Review: ')[0].split('Review-in-Progress: ')[-1].strip()
    product.url = context['url']
    product.ssid = context['url'].split('/')[4]
    product.category = 'Games'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = context['datetime'].split('T')[0]

    author = context['author']
    author_url = context['author_url']
    if author_url and author:
        review.authors.append(Person(name=author, profile_url=author_url, ssid=author))
    else:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[@class="article-lead-middle"]//p/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@class="article-content-wrapper in"]//p[following-sibling::div[@class="author-short-bio"]]//text()').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        review.add_property(type='excerpt', value=excerpt)
        product.reviews.append(review)
        session.emit(product)