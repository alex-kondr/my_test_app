from agent import *
from models.products import *
import time
import random
import HTMLParser


h = HTMLParser.HTMLParser()
XCAT = ['Community', 'Announcements', 'Events']


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://icrontic.com/', max_age=0), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    revs = data.xpath('//div[div[@class="Title"]]')
    for rev in revs:
        title = rev.xpath('div[@class="Title"]/a/text()').string()
        url = rev.xpath('div[@class="Title"]/a/@href').string()
        cat = rev.xpath('.//span[contains(@class, "Category")]//text()').string(multiple=True)

        if cat not in XCAT:
            session.queue(Request(url, max_age=0), process_review, dict(cat=cat, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    data.content = h.unescape(data.content)

    product = Product()
    product.name = h.unescape(context['title']).replace('///SOLD\\\\\\', '').replace(' Reviews [SPOILERS]', '').replace(' Review', '').replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']

    review = Review()
    review.type = 'user'
    review.title = h.unescape(context['title']).replace('&', '&')
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//a[not(@name)]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("//div[@class='Item-Header DiscussionHeader']/div[@class='AuthorWrap']/span[@class='Author']/a[@class='Username']/text()").string()
    author_url = data.xpath("//div[@class='Item-Header DiscussionHeader']/div[@class='AuthorWrap']/span[@class='Author']/a[@class='Username']/@href").string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//p[normalize-space(strong/text())="Conclusion"]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath("//div[@class='Discussion']/div[@class='Item-BodyWrap']/div[@class='Item-Body']/div[@class='Message userContent']//text()[not(preceding::p[normalize-space(strong/text())='Conclusion'] or normalize-space(.)='Conclusion')]").string(multiple=True)
    if excerpt:
        excerpt = h.unescape(excerpt).strip()
        if len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
