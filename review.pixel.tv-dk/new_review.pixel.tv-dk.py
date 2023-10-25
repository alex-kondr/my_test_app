from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://pixel.tv/category/gaming/', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="grid-container-shadow"]')
    for rev in revs:
        title = rev.xpath('.//h3[@class="title"]/text()').string()
        author = rev.xpath('.//p[@class="author"]/text()').string()
        date = rev.xpath('.//p[@class="date"]/text()').string()
        url = rev.xpath(".//a/@href").string()
        session.queue(Request(url), process_review, dict(context, title=title, author=author, date=date, url=url))

    if revs:
        page = context.get('page', 0) + 1
        url = 'https://pixel.tv/wp-admin/admin-ajax.php'
        options = "--compressed -X POST -H 'X-Requested-With: XMLHttpRequest' --data-raw 'action=load_more_posts&page=" + str(page) +"&category_id=7'"
        session.queue(Request(url, use='curl', options=options, force_charset='utf-8', max_age=0), process_revlist, dict(page=page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Anmeldelse: ', '').replace('anmeldelse', '')
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = "Gaming"

    review = Review()
    review.title = context['title']
    review.type = 'pro'
    review.url = product.url
    review.ssid = product.ssid
    review.date = context['date']

    if context['author']:
        review.authors.append(Person(name=context['author'], ssid=context['author']))

    summary = data.xpath('//div[@class="hero-container"]/p/text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//p[contains(., "Se med på")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
