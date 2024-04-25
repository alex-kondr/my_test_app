from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request('http://megaobzor.com/news-topic-15-page-1.html'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="txt"]//a')
    for rev in revs:
        title = rev.xpath('b/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('review-', '').replace('.html', '')
    product.category = 'Технологии'

    product.name = data.xpath('//span[@id="model_name"]/text()').string()
    if not product.name:
        product.name = context['title'].split('Обзор')[-1]

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    rev_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if rev_json:
        rev_json = simplejson.loads(rev_json.replace(context['title'], ''))

        date = rev_json.get('datePublished')
        if date:
            review.date = date.split()[0]

        author = rev_json.get('author', {}).get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

    if not review.authors:
        author = data.xpath('//div[@class="artinfo"]//text()').strint(multiple=True)
        if author:
            author = author.split('Автор -')[-1].split('Размещено')[0].strip('.').strip()
            review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//h3[contains(., "Итоги")]/following-sibling::text()[not(contains(., "Реклама"))]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Итоги")]/preceding-sibling::text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="bodytext"]/text()[not(contains(., "Реклама"))]').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
