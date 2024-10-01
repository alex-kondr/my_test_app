from agent import *
from models.products import *


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.eurogamer.nl/archive/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="archive__title"]/a')
    for rev in revs:
        title = rev.xpath("text()").string()
        url = rev.xpath("@href").string()
        if title and url:
            session.queue(Request(url), process_review, dict(context, url=url, title=title))

    next_url = data.xpath('//a[span[@aria-label="Volgende pagina"]]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' review')[0].split(' Review – ')[0].split(' Review - ')[0].replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('-reviews', '').replace('-review', '')
    product.category = "Games"

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

    grade_overall = data.xpath('//span[@class="review_rating_value"]/text()').string()
    if grade_overall:
        grade_overall_max = data.xpath('//span[@class="review_rating_max_value"]/text()').string()
        review.grades.append(Grade(type="overall", value=float(grade_overall), best=float(grade_overall_max)))

    if not grade_overall:
        grade_overall = data.xpath('//div[@class="review_rating"]/@data-value').string()
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

    summary = data.xpath('//p[@class="strapline"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//section[@class="synopsis"]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//section[not(@class)]/p[not(contains(., "Voor onze"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "article_body_content")]/p[not(contains(., "Voor onze"))]//text()').string(multiple=True)

    context['excerpt'] = excerpt

    next_url = data.xpath('//div[@class="next"]/a/@href').string()
    if next_url:
        page = 1
        title = review.title + " - Pagina " + str(page)
        review.add_property(type='pages', value=dict(title=title, url=review.url))

        session.do(Request(next_url), process_review_next, dict(context, product=product, review=review, page=page + 1))

    else:
        context['product'] = product
        context['review'] = review
        process_review_next(data, context, session)


def process_review_next(data, context, session):
    review = context['review']

    page = context.get('page', 1)
    if page > 1:
        title = review.title + " - Pagina " + str(page)
        url = data.xpath('//link[@rel="canonical"]/@href').string()
        review.add_property(type='pages', value=dict(title=title, url=url))

        excerpt = data.xpath('//section[not(@class)]/p[not(contains(., "Voor onze"))]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[contains(@class, "article_body_content")]/p[not(contains(., "Voor onze"))]//text()').string(multiple=True)

        if excerpt:
            context['excerpt'] += " " + excerpt

    next_url = data.xpath('//div[@class="next"]/a/@href').string()
    if next_url:
        session.do(Request(next_url), process_review_next, dict(context, page=page + 1))

    elif context['excerpt']:
        review.add_property(type="excerpt", value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)
        session.emit(product)
