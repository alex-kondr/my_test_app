from agent import *
from models.products import *


REVS = []


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://hardware.info/reviews.html', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[@class="overview-item__body"]')
    for rev in revs:
        title = rev.xpath('h3/a/text()').string()
        cat = rev.xpath('span[contains(@class, "category") and not(contains(., "Review"))]/text()').string()
        url = rev.xpath('h3/a/@href').string()

        if url not in REVS:
            REVS.append(url)
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, cat=cat, url=url))
        else:
            return

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].replace('Review:', '').replace('Eerste blik: ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat'] or 'Techniek'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//span[@class="article__date"]/text()').string()
    if date:
        review.date = date.rsplit(' ', 1)[0]

    author = data.xpath('//span[contains(@class, "article__author")]//text()').string(multiple=True)
    if author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//h2[contains(., "Conclusie")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusie")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="article__content"]//p//text()').string(multiple=True)

    next_page = data.xpath('//a[contains(@class, "next")]').first()
    if next_page:
        title = review.title + ' - Pagina 1'
        review.add_property(type='pages', value=dict(title=title, url=data.response_url))

        next_title = next_page.xpath('strong/text()').string()
        next_url = next_page.xpath('@href').string()
        review.add_property(type='pages', value=dict(title=next_title, url=next_url))
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_review_next, dict(excerpt=excerpt, review=review, product=product))

    elif excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_next(data: Response, context: dict[str, str], session: Session):
    block = data.xpath('//h1[contains(., "Sorry, je gaat even iets te snel")]')
    if block:
        session.queue(Request(data.response_url, use='curl', force_charset='utf-8', max_age=0), process_review_next, dict(context))
        return

    review = context['review']

    conclusion = data.xpath('//h2[contains(., "Conclusie")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusie")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt and not conclusion:
        excerpt = data.xpath('//div[@class="article__content"]//p//text()').string(multiple=True)

    if excerpt:
        context['excerpt'] += ' ' + excerpt

    next_page = data.xpath('//a[contains(@class, "next")]').first()
    if next_page:
        title = next_page.xpath('strong/text()').string()
        url = next_page.xpath('@href').string()
        review.add_property(type='pages', value=dict(title=title, url=url))
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review_next, dict(context, review=review))

    elif context['excerpt']:
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)