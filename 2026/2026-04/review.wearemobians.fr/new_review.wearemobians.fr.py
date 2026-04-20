from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('http://wearemobians.com/category/articles/', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' : ')[0].replace('[Test / Concours] ', '').replace('[Test]', '').replace('[TEST] ', '').replace('[TEST] ', '').replace('[CONCOURS] ', '').replace('test be.ez ', '').replace('Test du ', '').replace('Test de ', '').replace(' (test express)', '').replace('Test ', '').strip()
    product.ssid = context['url'].split('/')[-2]

    product.url = data.xpath('//a[contains(@href, "amazon.fr")]/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = data.xpath('//a[@rel="category" and not(regexp:test(., "Articles|Actualités|Test", "i"))]/text()').string()
    if not product.category:
        product.category = 'Technologie'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time[@class="post-date"]/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[contains(., "Note Globale")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.split(':')[-1].replace('%', '')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append((Grade(type='overall', value=float(grade_overall), best=100.0)))

    grades = data.xpath('(//p[contains(., "Note Globale")]/following-sibling::*)[1]/li')
    for grade in grades:
        grade = grade.xpath('.//text()').string(multiple=True)
        grade_name = grade.split(' – ')[0].strip()
        grade_val = grade.split(' – ')[-1].split('%')[0]
        if grade_name and grade_val and float(grade_val) > 0:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100.0))

    pros = data.xpath('//tbody[contains(tr, "On a aimé ")]/tr[not(contains(., "On a aimé"))]/td[1]')
    if not pros:
        pros = data.xpath('(//p[contains(., "J’ai aimé")]/following-sibling::*)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//tbody[contains(tr, "et moins aimé")]/tr[not(contains(., "On a aimé "))]/td[2]')
    if not cons:
        cons = data.xpath('(//p[contains(., "Je n’ai pas aimé")]/following-sibling::*)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//p[contains(strong, "Conclusion")]//text()[not(contains(., "Conclusion"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(., "Conclusion")]/following-sibling::p[not(regexp:test(., "J’ai aimé|Je n’ai pas aimé") or .//i)]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[contains(strong, "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(contains(strong, "technique") or contains(., "https://www.") or contains(., "D’autres articles qui pourraient vous intéresser") or preceding::text()[contains(., "D’autres articles qui pourraient vous intéresser")] or contains(., "@"))]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
