from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.fudzilla.com/reviews', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('(//h4[contains(@class, "title")]|//h3[@class="catItemTitle"])/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if ' vs. ' not in title:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    if revs:
        offset = context.get('offset', 0) + 5
        next_url = 'https://www.fudzilla.com/reviews?start={}&tmpl=component'.format(offset)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(offset=offset))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' Review: ')[0].split(' Review - ')[0].replace(' put to the test', '').replace(' previewed', '').replace(' reviewed', '').replace(' Reviewed', '').replace(' review', '').replace(' Sample Tested', '').replace(' tested', '').replace(' Preview', '').replace(' Review', '').replace(' getestet', '').replace(' im Test', '').replace('The fastest ', '').replace(', more tests', '').strip()
    product.ssid = context['url'].split('-')[0].split('/')[-1]
    product.category = 'Tech'

    product.url = data.xpath('//a[contains(@href, "amzn.to") or contains(., "Amazon")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//span[@class="itemDateCreated"]/text()').string(multiple=True)

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[@class="itemIntroText" and not(contains(., "Page 1 of"))]//text()[not(contains(., "Review:"))]').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "Should you go|Conclusion")]/following-sibling::p//text()[not(regexp:test(., "customers can get |Amazon"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//strong[contains(., "Conclusion")]/following-sibling::text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Should you go|Conclusion")]/preceding-sibling::p//text()[not(regexp:test(., "customers can get |Amazon"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="itemFullText"]/p[not(regexp:test(., "Conclusion|Specs:|Standard:"))]//text()[not(regexp:test(., "customers can get |Amazon"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//div[@class="itemFullText"]|//div[@class="itemFullText"]/strong)/text()').string(multiple=True)

    if excerpt and conclusion:
        excerpt = excerpt.replace(conclusion, '').strip()

    pages = data.xpath('//div[@id="article-index"]//a[not(contains(@href, "showall="))]')
    for page in pages:
        title = page.xpath("text()").string()
        url = page.xpath("@href").string()
        review.add_property(type="pages", value=dict(url=url, title=title))

    if pages:
        session.do(Request(url, use='curl', force_charset='utf-8', max_age=0), process_lastpage, dict(review=review, product=product, excerpt=excerpt))

    elif excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_lastpage(data, context, session):
    review = context['review']

    conclusion = data.xpath('//div[@class="itemFullText"]//p//text()[not(regexp:test(., "customers can get |Amazon"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//div[@class="itemFullText"]|//div[@class="itemFullText"]/strong)/text()[not(regexp:test(., "Test:"))]').string(multiple=True)

    if conclusion:
        if 'Conclusion' in conclusion or 'Fazit:' in conclusion:
            context['excerpt'] += conclusion.split('Conclusion')[0].split('Fazit:')[0]

            conclusion = conclusion.split('Conclusion')[-1].split('Fazit:')[-1].strip(' +-:')

        review.add_property(type='conclusion', value=conclusion)

    if context['excerpt']:
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
