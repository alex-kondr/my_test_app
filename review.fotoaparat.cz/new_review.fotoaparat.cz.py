from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('http://www.fotoaparat.cz/article/subcat/303/1', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//a[contains(@class, "title")]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(url=url))

    next_url = data.xpath('//li[contains(@class, "next")]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    title = data.xpath('//h1//text()').string()
    if not title:
        return

    product = Product()
    product.name = title.split(' test objektivu ')[-1].replace('Test Full frame kompaktu ', '').replace('Full frame kompakt ', '').replace('Test objektivu ', '').replace('Test ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = data.xpath('//div[@class="breadcrumbs"]/ul/li[last()]/a//text()').string(multiple=True) or 'Technologie'

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//li[i[contains(@class, "calendar")]]/text()').string(multiple=True)

    author = data.xpath('//li[i[contains(@class, "person")] and a[contains(@href, "https://www.fotoaparat.cz/clanky/autor/")]]/a/text()').string()
    author_url = data.xpath('//li[i[contains(@class, "person")] and a[contains(@href, "https://www.fotoaparat.cz/clanky/autor/")]]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//p[strong[contains(., "Klady")]]/following-sibling::p[not(preceding-sibling::p[regexp:test(., "Zápory")] or regexp:test(., "Zápory"))]')
    if not pros:
        pros = data.xpath('//table[thead/tr/td[contains(., "Dobrý")]]/tbody/tr/td[1]')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[contains(., "Zápory")]/following-sibling::p[not(contains(., "Děkuji společnosti"))]')
    if not cons:
        cons = data.xpath('//table[thead/tr/td[contains(., "Špatný")]]/tbody/tr/td[2]')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "article-perex")]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[strong[contains(., "Závěr")]]/following-sibling::p[not(preceding-sibling::p[strong[regexp:test(., "Klady|Zápory")]] or regexp:test(., "Klady|Zápory"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Závěr")]/following-sibling::p[not(preceding-sibling::p[strong[regexp:test(., "Klady|Zápory")]] or regexp:test(., "Klady|Zápory"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[strong[contains(., "Závěr")]]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[not(@class)]/p[not(preceding-sibling::p[strong[regexp:test(., "Klady|Zápory")]] or regexp:test(., "Klady|Zápory"))]//text()').string(multiple=True)

    next_page = data.xpath('//li[@class="pagination-next"]/a/@href').string()
    if next_page:
        title = review.title + ' - Pagina 1'
        review.add_property(type='pages', value=dict(title=title, url=data.response_url))
        session.do(Request(next_page, use='curl', force_charset='utf-8'), process_review_next, dict(excerpt=excerpt, review=review, product=product))

    elif excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_next(data, context, session):
    review = context['review']

    page = context.get('page', 1) + 1
    title = review.title + ' - Pagina ' + str(page)
    review.add_property(type='pages', value=dict(title=title, url=data.response_url))

    pros = data.xpath('//p[strong[contains(., "Klady")]]/following-sibling::p[not(preceding-sibling::p[regexp:test(., "Zápory")] or regexp:test(., "Zápory"))]')
    if not pros:
        pros = data.xpath('//table[thead/tr/td[contains(., "Dobrý")]]/tbody/tr/td[1]')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[contains(., "Zápory")]/following-sibling::p[not(contains(., "Děkuji společnosti"))]')
    if not cons:
        cons = data.xpath('//table[thead/tr/td[contains(., "Špatný")]]/tbody/tr/td[2]')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//p[strong[contains(., "Závěr")]]/following-sibling::p[not(preceding-sibling::p[strong[regexp:test(., "Klady|Zápory")]] or regexp:test(., "Klady|Zápory"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Závěr")]/following-sibling::p[not(preceding-sibling::p[strong[regexp:test(., "Klady|Zápory")]] or regexp:test(., "Klady|Zápory"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[strong[contains(., "Závěr")]]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[not(@class)]/p[not(preceding-sibling::p[strong[regexp:test(., "Klady|Zápory")]] or regexp:test(., "Klady|Zápory"))]//text()').string(multiple=True)

    if excerpt:
        context['excerpt'] += ' ' + excerpt

    next_page = data.xpath('//li[@class="pagination-next"]/a/@href').string()
    if next_page:
        session.do(Request(next_page, use='curl', force_charset='utf-8'), process_review_next, dict(context, review=review, page=page))

    elif context['excerpt']:
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
