from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.drohnen.de/category/testberichte/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="entry-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@class="next page-numbers"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('[Test & Vergleich]', '').replace(': Test / Vergleich / Bewertung', '').replace('– Test / Vergleich / Bewertung', '').replace('– Test / Vergleich', '').replace('Vergleich und Test', '').replace(': Test, Vergleich und Erfahrungen', '').replace('im Test & Vergleich', '').replace(': Test & Erfahrungen', '').replace(': Test & Erfahrungen', '').replace(': Test der Enterprise-Drohne', '').replace(': Test & Review', '').replace(': Test und Angebote', '').replace(u'\u2013 Test und Angebote', '').replace(': Test und Erfahrungen', '').replace(': Test und Erfahrung', '').replace('im Test', '').strip()
    product.ssid = context['url'].split('/')[-3]

    product.url = data.xpath('(//div[@class="aawp-product__thumb" and not(preceding-sibling::*[contains(., "Bestseller")])]/a|//a[contains(@href, "store.dji.com")])/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = data.xpath('//a[@rel="tag" and not(contains(., "Test") or contains(., "News"))]/text()').string()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//span[@itemprop="datePublished"]/@datetime').string()

    author = data.xpath('//span[@itemprop="author"]//text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="final-score"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//div[@class="ratings"]//div[@class="label"]')
    for grade in grades:
        grade_name, grade_val = grade.xpath('text()').string().split(' - ')
        grade_val = grade_val.replace('%', '')
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100.0))

    pros = data.xpath('//div[@class="pros-gardena"]//li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="cons-gardena"]//li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="review-long-summary"]/p/text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('(//h2|//h3)[contains(., "Fazit")][last()]/preceding-sibling::p[not(.//*[contains(@style, "color") or contains(@style, "decoration") or .//*[contains(@class, "button")]])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//h2|//h3)[contains(., "Fazit")][last()]/preceding::p[not(.//*[contains(@style, "color") or contains(@style, "decoration")] or contains(., "Fazit:") or .//*[contains(@class, "button")])]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

    conclusion = data.xpath('(//h2|//h3)[contains(., "Fazit")][last()]/following-sibling::p[not(.//*[contains(@style, "color") or contains(@style, "decoration")])]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

        product.reviews.append(review)

        session.emit(product)
