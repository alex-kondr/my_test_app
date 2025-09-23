from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://lemondenumerique.ouest-france.fr/tests/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h4/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review_short, dict(url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review_short(data, context, session):
    name = data.xpath('//p[contains(., " lire ")]/a/text()').string()
    url = data.xpath('//p[contains(., " lire ")]/a/@href').string()
    if url and 'lemondenumerique.ouest-france.fr' in url:
        session.do(Request(url, use='curl', force_charset='utf-8'), process_review, dict(name=name, url=url))
    else:
        process_review(data, context, session)


def process_review(data, context, session):
    title = data.xpath('//h1/text()').string()

    product = Product()
    product.name = (context.get('name') or title).split('test du')[-1].split('test de')[-1].replace('test complet du ', '').replace('test complet de la ', '').replace('Test de la ', '').replace('test complet de ', '').replace('Test du ', '').replace('Test de ', '').replace(' : notre Test', '').replace(' testé', '').replace('Test ', '').replace(' en test', '').replace('Tests des ', '').replace('Tests de la ', '').replace('Tests de ', '').replace('Tests matériels ', '').replace('Tests du ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Technologie'

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('(//span[contains(@class, "author")])[1]//text()').string(multiple=True)
    author_url = data.xpath('//span[contains(@class, "author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grades_name = data.xpath('//h5[@class="global-note"]|//div[@class="note"]/h5')
    grades_val = data.xpath('//script[contains(., "score:")]/text()').string()
    if grades_val:
        grades_val = re.findall(r'score:\s+\d\.?\d?', grades_val)

    if grades_name and grades_val:
        for grade_name, grade_val in zip(grades_name, grades_val):
            grade_name = grade_name.xpath('.//text()').string()
            grade_val = grade_val.replace('score:', '').strip()
            if 'Note globale' in grade_name:
                review.grades.append(Grade(type='overall', value=float(grade_val), best=5.0))
            else:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    conclusion = data.xpath('//div[@class="avis_test"]//text()[not(contains(., "Notre avis"))]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="article-content"]/p[not(contains(., "id=”"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
