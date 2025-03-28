from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.vg247.com/archive/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="archive__title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[span[@aria-label="Next page"]]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('review:')[0].split('review -')[0].split(' Review')[0].split('review –')[0].split('review-')[0].split(' reviews ')[0].strip()
    product.ssid = context['url'].split('/')[-1].replace('-review', '')
    product.category = 'Games'
    product.manufacturer = data.xpath('//li[strong[contains(., "Developer")]]/text()').string(multiple=True)

    product.url = data.xpath('//li[strong[contains(., "Link")]]/a/@href').string()
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

    author = data.xpath('//span[@class="author"]/a/text()').string()
    author_url = data.xpath('//span[@class="author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review_rating"]/@data-value').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    summary = data.xpath('//p[@class="strapline"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Final Thoughts")]/following-sibling::p[not(preceding-sibling::hr)]//text()[not(contains(., "Conclusion"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h4[contains(., "Verdict")]/following-sibling::p[not(preceding-sibling::hr)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[contains(., "Conclusion")]][last()]//text()[not(contains(., "Conclusion"))]').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Final Thoughts")]/preceding-sibling::p//text()[not(contains(., "Conclusion"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h4[contains(., "Verdict")]/preceding-sibling::p[not(preceding-sibling::hr)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[strong[contains(., "Conclusion")]]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "article_body_conten")]/p[not(preceding-sibling::hr)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
