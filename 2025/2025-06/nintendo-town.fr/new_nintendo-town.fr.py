from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.nintendo-town.fr/category/test/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if not next_url:
        next_url = data.xpath('//a[@class="page_nav next"]/@href').string()

    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.ssid = context['url'].split('/')[-2].replace('test-', '')

    product.name = re.sub(r'Test de la manette|Test rapide du la manette|Test rapide de la manette|Présentation et test de la|Test complet de la|Test matos|Test du casque|Test |Test Matos –|Test matos – |La Preview|\(.+\)', '', context['title'], flags=re.UNICODE).split(' – ')[0].strip()
    if not product.name:
        product.name = context['title'].replace('Test matos – ', '').strip()

    category = data.xpath('//a[@rel="category tag" and not(regexp:test(., "Test matériel|Test Chaud") or normalize-space(text())="Tests")]/text()').string()
    if category:
        product.category = category.replace('Tests ', '').replace('Preview ', '').strip()
    else:
        product.category = 'Technologie'

    product.url = data.xpath('//a[contains(@class, "amazon")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if not date:
        date = data.xpath('//div[contains(@class, "meta_date")]/a/text()').string()

    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "meta_author")]/a//text()').string()
    author_url = data.xpath('//div[contains(@class, "meta_author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="score_value"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('(//div[contains(@class, "reviewscore")]/ul)[1]/li')
    for grade in grades:
        grade_name = grade.xpath('strong/text()').string()
        grade_val = float(grade.xpath('.//span/@data-width').string()) / 10
        review.grades.append(Grade(name=grade_name, value=grade_val, best=10.0))

    pros = data.xpath('//div[h3[contains(., "LES PLUS")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[h3[contains(., "LES MOINS")]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[contains(@class, "post_subtitle")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[@class="desc"]/p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[contains(., "Conclusion")]/following::p[not(@class or contains(., "©"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="content-inner"]/p[not(@class or contains(., "©"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
