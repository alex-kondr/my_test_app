from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('http://www.channelpostmea.com/category/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[@rel="bookmark"]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@class="nextpostslink"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review:', '').strip()
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]

    categories = data.xpath('//a[@rel="category tag" and not(contains(., "Review") or contains(., "Articles") or contains(., "Products") or contains(., "Newsletter"))]/text()').strings()
    if categories:
        product.category = '/'.join(categories)
    else:
        product.category = 'Technik'

    review = Review()
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "entry-byline-author")]/span[@itemprop="author"]/a//text()').string(multiple=True)
    author_url = data.xpath('//div[contains(@class, "entry-byline-author")]/span[@itemprop="author"]/a/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//span[contains(., "Verdict")]/following::span[@itemprop="publisher"]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.split('Price:')[0].split('Comments')[0]
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//span[contains(., "Verdict")]/preceding::span[@itemprop="publisher"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//span[contains(., "Price:")]/preceding::span[@itemprop="publisher"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//span[@style and contains(., "Comments")]/preceding::span[@itemprop="publisher"]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
