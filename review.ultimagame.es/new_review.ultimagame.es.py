from agent import *
from models.products import *


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.ultimagame.es/juegos', use='curl'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//div[a[@class="post_desta"]]/a')
    for rev in revs:
        name = rev.xpath('.//text()').string(multiple=True)
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl'), process_review, dict(name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Juegos'
    product.manufacturer = data.xpath('//span[@itemprop="author"]//span[@itemprop="name"]//text()').string(multiple=True)

    platforms = data.xpath('//div[contains(text(), "Juego para") and not(@class)]//span/text()').join('/')
    if platforms:
        product.category += '|' + platforms

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//strong[@itemprop="name"]/text()').string()
    review.url = product.url
    review.ssid = product.ssid

    summary = data.xpath('//div[@itemprop="description"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    next_page = data.xpath('//a[@title="Información Wiki"]/@href').string()
    session.do(Request(next_page), process_review_next, dict(review=review, product=product))


def process_review_next(data, context, session):
    strip_namespace(data)

    review = context['review']

    excerpt = data.xpath('//div[@class="intronoticia"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
