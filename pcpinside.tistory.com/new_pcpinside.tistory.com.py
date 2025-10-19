from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('http://pcpinside.tistory.com/', use='curl'), process_revlist, dict())


def process_revlist(data, context, session):
    rev_url = data.xpath("//div[@class='post-item']/a/@href").string()
    session.queue(Request(rev_url, use='curl'), process_review, dict(url=rev_url))

    revs_cnt = int(rev_url.split('/')[-1])
    for i in range(1, revs_cnt):
        next_url = rev_url.rsplit('/', 1)[0] + '/' + str(i)
        session.queue(Request(next_url, use='curl'), process_review, dict(url=next_url))


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('//div[@class="hgroup"]/h1/text()').string()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = data.xpath("//div[@class='category']//text()").string()

    review = Review()
    review.type = 'pro'
    review.title = product.name
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
