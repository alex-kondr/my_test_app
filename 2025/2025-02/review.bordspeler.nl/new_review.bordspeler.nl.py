from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://bordspeler.nl/category/op-reis/'), process_revlist, dict(cat='Op reis'))
    session.queue(Request('https://bordspeler.nl/category/op-tafel/'), process_revlist, dict(cat='Op tafel'))


def process_revlist(data, context, session):
    revs = data.xpath('//h4[@class="elementor-post__title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[@class="page-numbers next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat'] + "|" + 'Games'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//span[contains(@class, "item--type-date")]/text()').string(multiple=True)

    author = data.xpath('//span[contains(@class, "item--type-author")]/text()').string(multiple=True)
    if author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//h2[contains(., "Ten slotte")]/following-sibling::p[not(@style)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Ten slotte")]/preceding-sibling::p[not(@style)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "post-content")]//p[not(@style)]//text()').string(multiple=True)


    next_url = data.xpath('//a[@class="post-page-numbers"]/@href').string()
    if next_url:
        title = review.title + " - Pagina 1"
        review.add_property(type='pages', value=dict(title=title, url=review.url))

        session.do(Request(next_url), process_review_next, dict(context, product=product, review=review, excerpt=excerpt, page=2))

    else:
        context['product'] = product
        context['review'] = review
        context['excerpt'] = excerpt
        process_review_next(data, context, session)


def process_review_next(data, context, session):
    review = context['review']

    page = context.get('page', 1)
    if page > 1:
        title = review.title + " - Pagina " + str(page)
        review.add_property(type='pages', value=dict(title=title, url=data.response_url))

        conclusion = data.xpath('//h2[contains(., "Ten slotte")]/following-sibling::p[not(@style)]//text()').string(multiple=True)
        if conclusion:
            review.add_property(type='conclusion', value=conclusion)

        excerpt = data.xpath('//h2[contains(., "Ten slotte")]/preceding-sibling::p[not(@style)]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[contains(@class, "post-content")]//p[not(@style)]//text()').string(multiple=True)

        if excerpt:
            context['excerpt'] += ' ' + excerpt

    next_url = data.xpath('//a[@class="post-page-numbers" and contains(., "Pagina")]/@href').string()
    if next_url:
        session.do(Request(next_url), process_review_next, dict(context, review=review, page=page + 1))

    elif context['excerpt']:
        review.add_property(type="excerpt", value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)

