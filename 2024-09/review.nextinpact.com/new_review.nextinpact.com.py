from agent import *
from models.products import *
from datetime import datetime, timedelta


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://next.ink/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('(//h1[@class="article-title"]|//h2[@class="brief-title"])/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    end_date = data.xpath('//div[@data-ids and contains(., "Semaine Précédente")]/span[@id="previous"]/@data-date').string()
    if end_date:
        end_date_p = datetime.strptime(end_date, '%Y-%m-%d').date()
        begin_date = str(end_date_p - timedelta(7))

        next_url = 'https://next.ink/?begin={begin_date}&end={end_date}'.format(begin_date=begin_date, end_date=end_date)
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = data.xpath('//div[@class="public_categories"]//span[@class="category-text"]/text()').string()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:modified_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//p[@class="article-author"]/a[@class="author"]/text()').string()
    author_url = data.xpath('//p[@class="article-author"]/a[@class="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('=')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[@id="Introduction"]/p/strong/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@id="Introduction"]/p[not(strong)]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace('Next.ink :', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)