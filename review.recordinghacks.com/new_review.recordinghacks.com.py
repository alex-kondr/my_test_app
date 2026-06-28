from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://recordinghacks.com/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(h3, "Reviews")]/ul/li/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    # no next page


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' Review', '').replace(' Test', '').split(' review: ')[0].replace(' reviews', '').replace(' review', '').strip()
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="comment_post_ID"]/@value').string()
    product.category = 'Microphones'

    img = data.xpath("//div[@class='entrywrap']//img[contains(@src,'.jpg')]//@src").string()
    if img:
       product.add_property(type="image", value=dict(src=img))

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[contains(@id, "post")]/p[@class="date"]/text()').string()
    if not date:
        date = data.xpath('//p[contains(span, "Added:")]/text()[normalize-space()]').string()

    if date:
        review.date = date.split(',', 1)[-1].split('|')[0].strip()

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p[not(@class)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h4[contains(., "In Summary")]/following-sibling::p[not(@class or contains(., "Added:") or contains(span/text(), "Reviewer"))]//text()')
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xapth('//h4[contains(., "In Summary")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entrywrap"]/p[not(@class)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
