from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://evilgamerz.com/category/review/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//article[.//h2[@class="entry-title"]]')
    for rev in revs:
        name = rev.xpath('.//h2[@class="entry-title"]/a/text()').string()
        grade_overall = rev.xpath('.//div[@class="overlay"]/text()').string()
        cats = rev.xpath('.//a[contains(@href, "category") and not(contains(text(), "Review") or contains(text(), "Uitgelicht"))]/text()').strings()
        url = rev.xpath('.//h2[@class="entry-title"]/a/@href').string()
        session.queue(Request(url), process_review, dict(name=name, grade_overall=grade_overall, cats=cats, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Tech'

    prod_info = data.xpath('//div[@class="artikel_veld" and (contains(., "Auteur:") or contains(., "Genre:") or contains(., "Ontwikkelaar:"))]//text()').string(multiple=True)

    genre = [info for info in prod_info.split('|') if "Genre" in info]
    if genre and context['cats']:
        genre = genre[0].replace('Genre:', '').strip()
        product.category = '/'.join([cat.strip() for cat in context['cats']]) + '|' + genre
    elif context['cats']:
        product.category = '/'.join([cat.strip() for cat in context['cats']])

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

    author = [info for info in prod_info.split('|') if "Auteur" in info]
    if author:
        author = author[0].replace('Auteur:', '').strip()
        review.authors.append(Person(name=author, ssid=author))

    if context['grade_overall']:
        grade_overall = float(context['grade_overall'])
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    grades = data.xpath('//div[@class="artikel_veld" and not(contains(., "Auteur:") or contains(., "Genre:") or contains(., "Ontwikkelaar:"))]//text()').string(multiple=True)
    if grades:
        grades = grades.split('|')
        for grade in grades:
            grade_name, grade_val = grade.split(':')
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('//div[@class="plus_veld"]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' .+-*')


