from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.zeden.net/tests', use='curl'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[@class="article"]/h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(text(), "suivant")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].replace('ZeDen teste ', '').replace('Zeden teste ', '').replace('Test ZeDen : ', '').replace('Test Zeden : ', '').replace(' : Preview', '').replace('Preview : ', '').replace('Preview de ', '').replace(' : Test', '').replace('Test de ', '').replace('Test : ', '').replace('Mini-Preview de ', '').replace('[Test] ', '').replace('Test boitier ', '').replace(' : Le test qu', '').strip().capitalize()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].split('-')[0]

    if data.xpath('//div[@class="fildAriane"]/a[contains(text(), "Jeux")]'):
        product.category = 'Jeux'
    else:
        product.category = 'Technologie'

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

    if data.xpath('//img[@src="https://www.zeden.net/design/icones_evaluation/tresbon.png"]'):
        grade_overall = 5.0
    elif data.xpath('//img[@src="https://www.zeden.net/design/icones_evaluation/bon.png"]'):
        grade_overall = 4.0
    elif data.xpath('//img[@src="https://www.zeden.net/design/icones_evaluation/moyen.png" or @src="https://www.zeden.net/design/icones_evaluation/mauvais.png"]'):
        grade_overall = 3.0
    else:
        grade_overall = 0.0

    if grade_overall:
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//td[normalize-space(center//text())="Pour"]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//td[normalize-space(center//text())="Contre"]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    is_recommended = data.xpath('//img[@alt="Produit recommandé par ZeDen"]')
    if is_recommended:
        review.add_property(value=True, type='is_recommended')

    conclusion = data.xpath('//div[contains(h3, "Conclusion")]//text()[not(parent::h3)]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="zonePage" and not(.//@class="commentaires")]//text()[not(preceding::h3[contains(., "Conclusion")] or parent::h3)]').string(multiple=True)

    pages = data.xpath('//div[@class="liste"]/ol/li/h2/a')
    for page in pages:
        title = page.xpath('.//text()').string(multiple=True)
        page_url = page.xpath('@href').string()
        review.add_property(type='pages', value=dict(title=title, url=page_url))

    if pages:
        session.do(Request(page_url, use='curl'), process_review_last, dict(excerpt=excerpt, review=review, product=product))

    elif excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_last(data: Response, context: dict[str, str], session: Session):
    review = context['review']

    if data.xpath('//img[@src="https://www.zeden.net/design/icones_evaluation/tresbon.png"]'):
        grade_overall = 5.0
    elif data.xpath('//img[@src="https://www.zeden.net/design/icones_evaluation/bon.png"]'):
        grade_overall = 4.0
    elif data.xpath('//img[@src="https://www.zeden.net/design/icones_evaluation/moyen.png" or @src="https://www.zeden.net/design/icones_evaluation/mauvais.png"]'):
        grade_overall = 3.0
    else:
        grade_overall = 0.0

    if grade_overall:
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//td[normalize-space(center//text())="Pour"]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//td[normalize-space(center//text())="Contre"]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    is_recommended = data.xpath('//img[@alt="Produit recommandé par ZeDen"]')
    if is_recommended:
        review.add_property(value=True, type='is_recommended')

    conclusion = data.xpath('//div[@class="zonePage" and not(.//@class="commentaires")]//text()[not(parent::h3 or ancestor::table or ancestor::div[contains(@class, "navigation")])]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    if context['excerpt']:
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
