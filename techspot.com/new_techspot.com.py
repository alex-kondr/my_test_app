from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.techspot.com/reviews/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if ' vs ' not in title and ' vs. ' not in title:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' Re-Review:')[0].split(': The Fastest')[0].replace(' Review', '').replace(' Put to the Test', '').replace(' Tested', '').replace(' Tested', '').replace('Testing ', '').replace(' Testing', '').replace(' Test', '').replace(' Re-Review', '').split(' review: ')[0].replace(' review', '').replace(' Mini-Review', '').split(': Fastest ')[0].replace('Tested: ', '').replace(' Preview', '').strip()
    product.ssid = context['url'].split('/')[-2]
    product.category = data.xpath('//ul[@class="category-chicklets"]/li[not(contains(., "Review"))]//text()').string(multiple=True) or 'Tech'

    product.url = data.xpath('//a[contains(text(), "Amazon")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="author"]//text()').string(multiple=True)
    author_url = data.xpath('//span[@class="author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2].split('.')[-1] if 'https://www.techspot.com' in author_url else author_url.replace('https://', '').split('.')[0]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "rating")]/div/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    summary = data.xpath('//div[section[@class="title-group"]]/h2//text()').string(multiple=True)
    if summary:
        if ' vs ' in summary or ' vs. ' in summary:
            return

        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(text(), "Wrap Up|Recommendations|What We Learned", "i")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(text(), "Wrap Up|Recommendations|What We Learned", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="articleBody"]/p//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
