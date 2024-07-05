from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://evilgamerz.com/category/review/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="entry-title"]/a')
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Tech'

    cats = data.xpath('//div[@class="post-cat"]//span[contains(@class, "category-button") and not(contains(., "Review") or contains(., "Uitgelicht"))]')
    if cats:
        product.category = '/'.join([cat.xpath('.//text()').string(multiple=True) for cat in cats])

    prod_info = data.xpath('//div[@class="artikel_veld" and (contains(., "Auteur:") or contains(., "Genre:") or contains(., "Ontwikkelaar:"))]//text()').string(multiple=True)
    if prod_info:
        genre = [info for info in prod_info.split('|') if "Genre" in info]
        if genre and cats:
            genre = genre[0].replace('Genre:', '').strip()
            product.category += '|' + genre

        manufacturer = [info for info in prod_info.split('|') if "Ontwikkelaar" in info]
        if manufacturer:
            product.manufacturer = manufacturer[0].replace('Ontwikkelaar:', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//meta[@property="og:title"]/@content').string()
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    if prod_info:
        author = [info for info in prod_info.split('|') if "Auteur" in info]
        if author:
            author = author[0].replace('Auteur:', '').strip()
            review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@itemprop="ratingValue"]/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.replace(',', '.').replace('..', '.'))
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//div[@class="artikel_veld" and not(contains(., "Auteur:") or contains(., "Genre:") or contains(., "Ontwikkelaar:"))]//text()').string(multiple=True)
    if grades:
        grades = grades.split('|')
        for grade in grades:
            grade_name, grade_val = grade.split(':')
            if grade_val.strip():
                grade_val = float(grade_val.replace(',', '.').replace('..', '.'))
                review.grades.append(Grade(name=grade_name.strip(), value=grade_val, best=10.0))

    pros = data.xpath('//div[@class="plus_veld"]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' .+-*')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="min_veld"]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(' .+-*')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    excerpt = data.xpath('//div[@class="entry-content"]//p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
