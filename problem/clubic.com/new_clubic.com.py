from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.clubic.com/test-produit/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[a[contains(@class, "linked")] and p]')
    for rev in revs:
        title = rev.xpath('p/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' : ')[0].replace('Test ', '').strip()
    product.ssid = re.search(r'-\d+-', context['url'].split('/')[-1]).group().strip(' -')
    product.category = data.xpath('//ul[@id="breadcrumb-list"]/li[last()]//text()').string()

    product.url = data.xpath('//div[div[contains(., "Meilleurs prix")]]//a[@class="un-styled-linked"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//div[contains(., "Publié le ")]/text()').string()
    if date:
        review.date = date.replace('Publié le ', '').split(' à ')[0].strip()

    author = data.xpath('(//div[contains(text(), "Par")])[1]//text()[not(regexp:test(., "Par|\."))]').string()
    author_url = data.xpath('(//div[contains(text(), "Par")])[1]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].split('-')[0]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[div[svg]]//span//text()[not(contains(., "/") or contains(., "Voir plus de prix"))]').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//div[div[contains(text(), "Sous-notes")]]//div[span]')
    for grade in grades:
        grade_name = grade.xpath('div/text()').string()
        grade_val = grade.xpath('span/text()').string()
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('(//div[div[contains(text(), "Les plus")]]//ul)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//div[div[contains(text(), "Les moins")]]//ul)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[contains(., "Conclusion")]/following-sibling::div//p[not(preceding::div[contains(text(), "Sous-notes")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[.//h2[contains(., "Mon avis sur le")]]/following-sibling::div//p[not(preceding::div[contains(text(), "Sous-notes")])]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(., "Conclusion")]/preceding-sibling::div//p[@class]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[.//h2[contains(., "Mon avis sur le")]]/preceding-sibling::div//p[@class]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content")]//p[@class]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
