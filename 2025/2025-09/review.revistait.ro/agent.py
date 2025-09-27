from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('http://www.revistait.ro/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review: ', '').replace('Review ', '').replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '').replace('review-', '')

    product.category = data.xpath('//span[@class="thecategory"]//text()').string(multiple=True) or 'Tehnologie'
    product.category = product.category.replace(' , ', '|')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="theauthor"]//text()').string(multiple=True)
    author_url = data.xpath('//a[contains(@href, "https://www.revistait.ro/author/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//h4[contains(., "Concluzie")]/following-sibling::p[not(regexp:test(., "și solicită o evaluare gratuită!|<input|<br|<form|<\?php|form>|\$.|style>|//"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h4[contains(., "Concluzie")]/preceding-sibling::p[not(regexp:test(., "și solicită o evaluare gratuită!|<input|<br|<form|<\?php|form>|\$.|style>|//"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content")]/p[not(regexp:test(., "și solicită o evaluare gratuită!|<input|<br|<form|<\?php|form>|\$.|style>|//"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
