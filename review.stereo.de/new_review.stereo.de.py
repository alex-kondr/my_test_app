from agent import *
from models.products import *


XCAT = ['Alle Tests']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.stereo.de/test/', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[button[contains(., "Tests")]]/ul/li/a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_category, dict(cat=name))


def process_category(data, context, session):
    cat_id = data.xpath('//ol[contains(@id, "filter_ol")]//a[@class="nav-link term nodeko"]/@data-term').string()
    options = "--compressed -X POST --data-raw 'action=loop_filter_api&taxonomy={}&posts=&text=&template=tile&posts_per_page=1000&offset=0'".format(cat_id)
    url = 'https://www.stereo.de/wp-admin/admin-ajax.php'
    session.do(Request(url, use='curl', options=options, force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_revlist(data, context, session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, name=name, url=url))

# no next page


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].split('-')[-1]
    product.category = context['cat']
    product.manufacturer = data.xpath('//strong[contains(text(), "Hersteller:")]/following-sibling::span[1]/text()').string()

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[contains(@class, "title")]//text()').string(multiple=True)
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:modified_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    grade_overall = data.xpath('//small[@class="review__RatingMusic"]/@style').string()
    if grade_overall:
        grade_overall = grade_overall.split(':')[-1]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    excerpt = data.xpath('//div[@class="row"]/div/p[not(@class)]//text()').string(multiple=True)

    next_page = data.xpath('//a[contains(., "Artikel online lesen")]/@href').string()
    if next_page:
        session.do(Request(next_page, use='curl', force_charset='utf-8', max_age=0), process_review_next, dict(review=review, product=product))

    elif excerpt:
        summary = data.xpath('//p[@class="lead"]//text()').string(multiple=True)
        if summary:
            review.add_property(type='summary', value=summary)

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_next(data, context, session):
    review = context['review']

    review.title = data.xpath('//h1[contains(@class, "title")]//text()').string(multiple=True)

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@href, "https://www.stereo.de/autor/")]/text()').string()
    author_url = data.xpath('//a[contains(@href, "https://www.stereo.de/autor/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//p[contains(@class, "post-excerpt__excerpt")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@class="premium_content_html"]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
