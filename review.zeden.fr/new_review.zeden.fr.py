from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.zeden.net/tests'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(text(), "suivant")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].replace('ZeDen teste ', '').replace('Zeden teste ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].split('-')[0]
    product.category = 'Technologie'
    product.manufacturer = data.xpath('//a[contains(., "Fiche de")]/strong/text()').string()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//span[@class="heure"]/text()').string()

    author = data.xpath('//span[@style="float:right" and contains(text(), "par")]/a/text()').string()
    author_url = data.xpath('//span[@style="float:right" and contains(text(), "par")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('=')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//td[.//font[contains(text(), "Pour")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//td[.//font[contains(text(), "Contre")]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    is_recommended = data.xpath('//img[@alt="Produit recommandé par ZeDen"]')
    if is_recommended:
        review.add_property(value=True, type='is_recommended')

    excerpt = data.xpath('//div[@class="zonePage" and not(.//@class="commentaires")]/div[@style]/text()|//div[@class="zonePage" and not(.//@class="commentaires")]/div[@style]/a//text()').string(multiple=True)

    pages = data.xpath('//div[@class="liste"]/ol/li/h2')
    for page in pages:
        title = page.xpath('.//text()').string(multiple=True)
        page_url = page.xpath('a/@href').string()
        review.add_property(type='pages', value=dict(title=title, url=page_url))

    if pages:
        session.do(Request(page_url), process_review_last, dict(excerpt=excerpt, review=review, product=product))

    elif excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_last(data: Response, context: dict[str, str], session: Session):
    review = context['review']

    pros = data.xpath('//td[.//font[contains(text(), "Pour")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//td[.//font[contains(text(), "Contre")]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    is_recommended = data.xpath('//img[@alt="Produit recommandé par ZeDen"]')
    if is_recommended:
        review.add_property(value=True, type='is_recommended')

    conclusion = data.xpath('//div[@class="zonePage" and not(.//@class="commentaires")]/div[@style]/text()|//div[@class="zonePage" and not(.//@class="commentaires")]/div[@style]/a//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    if context['excerpt']:
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
