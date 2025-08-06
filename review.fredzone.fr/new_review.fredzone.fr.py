from agent import *
from models.products import *
import re


def run(context, session):
    session.queue(Request('https://www.fredzone.org/', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[a[contains(., "Tests")]]/ul/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' : Test')[0].split(' : Test')[0].replace('Test et avis du ', '').replace('Test du ', '').replace('Test : ', '').replace('Review : ', '').replace('Test de la ', '').strip()
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat']

    product.url = data.xpath('//a[contains(@href, "https://www.amazon.fr/")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="author vcard" and not(contains(., "La Rédaction"))]//text()').string(multiple=True)
    author_url = data.xpath('//span[@class="author vcard" and not(contains(., "La Rédaction"))]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//h1[regexp:test(., "Note Globale", "i")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = re.search(r'\d{1,2}[\.,]?\d{0,2}/10', grade_overall)
        if grade_overall:
            grade_overall = grade_overall.group().split('/')[0].replace(',', '.')
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//strong[regexp:test(., ".+:.+\d{1,2},?\d?/10") and not(regexp:test(., "Note Globale", "i"))]')
    for grade in grades:
        grade_name, grade_val = grade.xpath('.//text()').string(multiple=True).split(':')
        grade_name = grade_name.strip()
        grade_val = grade_val.split('/')[0].replace(',', '.').strip()
        if grade_name and float(grade_val) > 0:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('(//p[regexp:test(., "Points forts", "i")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p[regexp:test(., "Ponts faibles|Points faibles", "i")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p[not(regexp:test(., "Points forts|Ponts faibles|Design :|Performances :|Rapport qualité/prix :"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="entry-content"]/p[not(regexp:test(., "Points forts|Ponts faibles|Design :|Performances :|Rapport qualité/prix :") or preceding::h2[contains(., "Conclusion")])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
