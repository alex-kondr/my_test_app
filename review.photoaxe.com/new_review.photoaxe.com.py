from agent import *
from models.products import *


def run(context, session):
   session.queue(Request('http://www.photoaxe.com/category/cameras/'), process_revlist, {})


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "entry-title")]')
    for rev in revs:
        title = rev.xpath('a/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@class="next page-numbers"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, {})


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review', '').split('review')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]

    product.category = 'Cameras'
    category = data.xpath('//span[@class="cat-links"]/a/text()').strings()
    if category:
        product.category = '|'.join(category).replace(' Reviews', '').replace('Other ', '')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time[contains(@class, "entry-date")]/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//h2[@class="author-title"]/text()').string()
    if not author:
        author = data.xpath('//a[@rel="author"]/text()').string()
    if author:
        author = author.replace('By ', '').strip()
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//p//strong[contains(., "Conclusion")]/following::p[not(@class)]//text()[not(contains(., "Camera Specifications"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="entry-content"]/h3/text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.split('Specifications:')[0].split('Functions:')[0].split('Technical Data:')[0]
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p//strong[contains(., "Conclusion")]/preceding::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p//strong[contains(., "Specifications:")]/preceding::p[not(@class)]//text()[not(contains(., "Camera Specifications"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p//strong[contains(., "Functions:")]/preceding::p[not(@class)]//text()[not(contains(., "Camera Specifications"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p//strong[contains(., "Technical Data:")]/preceding::p[not(@class)]//text()[not(contains(., "Camera Specifications"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]/p//text()[not(contains(., "Camera Specifications"))]').string(multiple=True)
    if excerpt:
        excerpt = excerpt.split('Specifications:')[0].split('Functions:')[0].split('Other Technical data:')[0].split('Technical Data:')[0].split('Technical data:')[0].split('Technical data of')[0].strip()
        if 'Conclusion:' in excerpt:
            conclusion = excerpt.split('Conclusion:')[-1].strip()
            review.add_property(type='conclusion', value=conclusion)

            excerpt = excerpt.split('Conclusion:')[0].strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
