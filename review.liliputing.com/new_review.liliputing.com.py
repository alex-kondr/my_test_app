from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://liliputing.com/category/reviews', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].split(' Review: ')[0].split(' preview: ')[0].split(' Preview ')[0].split(' mini-review')[0].replace(' (mini-review)', '').replace('Review: ', '').replace(' Review', '').replace(' preview', '').replace(' review', '').replace(' Preview', '').replace('Review of ', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('review-', '').replace('-preview', '').replace('-review', '')
    product.category = 'Tech'

    product.url = data.xpath('//a[contains(@href, "amzn.to")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="author vcard"]//text()').string(multiple=True)
    author_url = data.xpath('//span[@class="author vcard"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//h2[regexp:test(., "Verdict|Conclusion")]/following-sibling::p[not(regexp:test(., "At time of publication", "i"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[regexp:test(., "Verdict|Conclusion")]]/following-sibling::p[not(regexp:test(., "At time of publication", "i"))]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Verdict|Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[strong[regexp:test(., "Verdict|Conclusion")]]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]/p[not(regexp:test(., "At time of publication", "i"))]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
