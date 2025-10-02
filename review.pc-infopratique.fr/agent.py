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
    session.queue(Request('https://www.pc-infopratique.com//dossier-debutr-0.html', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//b/a[contains(@href, "article-")]')
    for rev in revs:
        title = rev.xpath('.//text()').string()
        url = rev.xpath('@href').string()

        if ' et ' not in title:
            session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[img[contains(@src, "bout_suivant")]]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('Test du ', '').replace('Test de la ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('article-', '').split('-')[0]
    product.category = 'Ordinateurs'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//font[contains(text(), "Dossier publi")]/font[regexp:test(., "\d")]/text()').string()
    if date:
        review.date = date.split(' ', 1)[-1]

    author = data.xpath('//font[contains(text(), "Dossier publi")]/font[not(regexp:test(., "\d{4}"))]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//tbody[tr[contains(., "On aime")]]/tr[@valign="top"]//font//text()')
    if not pros:
        pros = data.xpath('//span[contains(., "Les +")]/following-sibling::text()[preceding-sibling::span[1][contains(., "Les +")]]')

    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//tbody[tr[contains(., "On n’aime pas")]]/tr[@valign="top"]//font//text()')
    if not cons:
        cons = data.xpath('//span[contains(., "Les -")]/following-sibling::text()[preceding-sibling::span[1][contains(., "Les -")]]')

    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//p[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//font[contains(@style, "FONT-FAMILY")]/p//text()').string(multiple=True)

    pages = data.xpath('//select[@name="select"]/option')
    for page in pages:
        title = page.xpath('text()').string()
        page_url = 'https://www.pc-infopratique.com' + page.xpath('@value').string()
        review.add_property(type='pages', value=dict(titel=title, url=page_url))

    if pages:
        session.do(Request(page_url, force_charset='utf-8'), process_review_last, dict(product=product, review=review, excerpt=excerpt))

    elif excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_last(data, context, session):
    review = context['review']

    pros = data.xpath('//tbody[tr[contains(., "On aime")]]/tr[@valign="top"]//font//text()')
    if not pros:
        pros = data.xpath('//span[contains(., "Les +")]/following-sibling::text()[preceding-sibling::span[1][contains(., "Les +")]]')

    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//tbody[tr[contains(., "On n’aime pas")]]/tr[@valign="top"]//font//text()')
    if not cons:
        cons = data.xpath('//span[contains(., "Les -")]/following-sibling::text()[preceding-sibling::span[1][contains(., "Les -")]]')

    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//font[contains(@style, "FONT-FAMILY")]/p[not(strong[regexp:test(., "Résumé|Informations complémentaires")])]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    if context['excerpt']:
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
