from agent import *
from models.products import *
import time


OPTIONS = """-H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Referer: https://icrontic.com/' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""
XCAT = ['Community', 'Announcements']
SLEEP = 5


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://icrontic.com/', use='curl', options=OPTIONS, max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    time.sleep(SLEEP)

    revs = data.xpath('//div[div[@class="Title"]]')
    for rev in revs:
        title = rev.xpath('div[@class="Title"]/a/text()').string()
        url = rev.xpath('div[@class="Title"]/a/@href').string()
        cat = rev.xpath('.//span[contains(@class, "Category")]//text()').string(multiple=True)

        if cat not in XCAT:
            session.queue(Request(url, use='curl', options=OPTIONS, max_age=0), process_review, dict(cat=cat, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', options=OPTIONS, max_age=0), process_revlist, dict())


def process_review(data, context, session):
    time.sleep(SLEEP)

    product = Product()
    product.name = context['title'].replace('///SOLD\\\\\\', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
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

    excerpt = data.xpath("//div[@class='Discussion']/div[@class='Item-BodyWrap']/div[@class='Item-Body']/div[@class='Message userContent']//text()").string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
