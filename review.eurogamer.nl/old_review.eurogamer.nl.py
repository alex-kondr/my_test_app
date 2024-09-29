from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.eurogamer.nl/archive/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//ul[@class='summary_list']/li/div/a")
    for rev in revs:
        title = rev.xpath("@title").string()
        url = rev.xpath("@href").string()
        if title and url:
            session.queue(Request(url), process_review, dict(context, url=url, title=title))

    next_url = data.xpath('//a[span[@title="Volgende pagina"]]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    prod_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)
    else:
        return

    product = Product()
    product.name = context['title'].split(' review')[0]
    product.url = context['url']
    product.category = "Games"
    product.ssid = product.url.split('/')[-1]

    review = Review()
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.type = 'pro'

    date = prod_json.get('datePublished')
    if date:
        review.date = date.split('T')[0]

    authors = prod_json.get('author', [])
    if not isinstance(authors, list):
        authors = [authors]

    for author in authors:
        author_name = author.get('name')
        author_url = author.get('url')
        if author_url and author_name:
            if isinstance(author_url, list):
                author_ssid = author_url[0].split('/')[-1]
            else:
                author_ssid = author_url.split('/')[-1]
            review.authors.append(Person(name=author_name, url=author_url, ssid=author_ssid))

    grade_overall = prod_json.get('reviewRating', {}).get('ratingValue', 0)
    grade_best = prod_json.get('reviewRating', {}).get('bestRating')
    if float(grade_overall) > 0:
        review.grades.append(Grade(type="overall", value=float(grade_overall), best=float(grade_best)))

    summary = data.xpath('//p[@class="strapline"]/text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = prod_json.get('description')
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    context['excerpt'] = data.xpath('//div[@class="article_body_content"]/section[@class="synopsis"]/text()|//div[@class="article_body_content"]//p//text()').string(multiple=True)

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

        excerpt = data.xpath('//div[@class="article_body_content"]//p//text()|//div[@class="article_body_content"]/h2//text()').string(multiple=True)
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
