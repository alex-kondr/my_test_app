from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://logout.hu/cikkek/index.html', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h4[@class="media-heading"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' Tech Review', '').replace(' Review', '').replace(u'\uFEFF', '').strip(' .')
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('_tech_review', '').replace('_review', '')
    product.category = 'Technológia'

    review = Review()
    review.type = 'pro'
    review.title = context['title'].replace(u'\uFEFF', '')
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/span/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].replace('.html', '')
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//p[@itemprop="description about"]//text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2|//p)[regexp:test(., "Végszó|Fnatic|Konklúzió")]/following-sibling::p[@class][not(s)]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2|//p)[regexp:test(., "Végszó|Fnatic|Konklúzió")]/preceding-sibling::p[@class][not(starts-with(normalize-space(.), "-"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content-body")]/p[@class][not(starts-with(normalize-space(.), "-"))]//text()').string(multiple=True)

    pages = data.xpath('//li/div[contains(@class, "dropdown-menu-limit")]/a')
    for page in pages:
        title = page.xpath('text()').string()
        page_url = page.xpath('@href').string()
        review.add_property(type='pages', value=dict(url=page_url, title=title))

    if pages:
        session.queue(Request(page_url, force_charset='utf-8'), process_review_last, dict(excerpt=excerpt, review=review, product=product))

    elif excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_last(data, context, session):
    review = context['review']

    conclusion = data.xpath('(//h2|//p)[regexp:test(., "Végszó|Fnatic|Konklúzió")]/following-sibling::p[@class][not(s)]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2|//p)[regexp:test(., "Végszó|Fnatic|Konklúzió")]/preceding-sibling::p[@class][not(starts-with(normalize-space(.), "-"))]//text()').string(multiple=True)
    if not excerpt and not conclusion:
        excerpt = data.xpath('//div[contains(@class, "content-body")]/p[@class][not(starts-with(normalize-space(.), "-"))]//text()').string(multiple=True)

    if excerpt:
        context['excerpt'] += ' ' + excerpt

    if context['excerpt']:
        context['excerpt'] = context['excerpt'].replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
