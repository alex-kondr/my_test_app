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
    product.ssid = product.url.split('/')[-1]
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
    review.date = data.xpath('//text()[contains(., "Juego analizado por")]/following-sibling::text()').string()

    author = data.xpath('//text()[contains(., "Juego analizado por")]/following-sibling::strong[1]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//div[div[contains(text(), "Deberías jugar")]]/text()[normalize-space(.)]').string(multiple=True)
    if pros:
        pros = pros.split('+')
        for pro in pros:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[div[contains(text(), "No deberías jugar")]]/text()[normalize-space(.)]').string(multiple=True)
    if cons:
        cons = cons.split('-')
        for con in cons:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@itemprop="description"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[h3[contains(text(), "Análisis")]]/div/span//text()').string(multiple=True)

    pages = data.xpath('//ul[@class="wiki"]/li[not(div)]/a')
    for page in pages:
        title = page.xpath('text()').string()
        page_url = page.xpath('@href').string()
        review.add_property(type='pages', value=dict(title=title, url=page_url))

    if pages:
        session.do(Request(page_url, use='curl'), process_review_next, dict(excerpt=excerpt, review=review, product=product))


def process_review_next(data, context, session):
    strip_namespace(data)

    review = context['review']

    excerpt = data.xpath('//div[@class="intronoticia"]//text()').string(multiple=True)
    if context['excerpt'] and excerpt:
        context['excerpt'] += ' ' + excerpt

    excerpt = context['excerpt'] if context['excerpt'] else excerpt
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
