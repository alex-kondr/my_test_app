from agent import *
from models.products import *
import time


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('http://pcpinside.tistory.com/', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//div[@class='post-item']/a")
    for rev in revs:
        title = rev.xpath("span[@class='title']/text()").string(multiple=True)
        url = rev.xpath("@href").string()

        if not context.get('revs_cnt'):
            context['revs_cnt'] = int(url.split('/')[-1])

        session.queue(Request(url, max_age=0), process_review, dict(title=title, url=url))

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        next_url = 'http://pcpinside.tistory.com/?page=' + str(next_page)
        session.queue(Request(next_url, max_age=0), process_revlist, dict(context, page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1]
    product.category = data.xpath("//div[@class='category']//text()").string()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@property="og.article.author"]/@content').string()
    if author and author != '알 수 없는 사용자':
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//div[@class="contents_style"]/p[not(.//a)][not(.//img)][not(b)][not(contains(@style, "TEXT-ALIGN: center"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
        
        time.sleep(10)
