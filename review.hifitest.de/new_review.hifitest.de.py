from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.hifitest.de/testberichte', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "testOverviewPart")]/a/@href')
    for rev in revs:
        url = rev.string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(url=url))

    next_url = data.xpath('//a[img[@alt="eine Seite vor"]]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    title = data.xpath('//*[@class="singleTestHeadline"]//text()').string(multiple=True)
    if not title:
        title = context['title']

    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]
    product.category = 'Technik'

    product.name = data.xpath('//p[contains(span/text(), "Produkt:")]/text()').string()
    if not product.name:
        product.name = title.replace('Chassistest:', '').replace('Vergleichstest:', '').replace('Filmrezension:', '').replace('Einzeltest:', '').replace(' im Dreiertest', '').replace(' im Doppeltest', '').replace('(Prokino)', '').replace('im Vergleich', '').replace('Serientest:', '').replace('Systemtest:', '').replace(' im Test', '').replace('Test: ', '').replace('Testbericht: ', '').replace('Musikrezension: ', '').replace('Test ', '').strip()

    cat = data.xpath('//span[@class="h3category"]/text()').string()
    if cat:
        product.category = cat.replace('Kategorie:', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//tr[contains(., "Datum")]/td[not(contains(., "Datum"))]/text()').string()
    if date:
        review.date = date.split(',')[0]

    author = data.xpath('//tr[contains(., "Autor")]//a/text()').string()
    author_url = data.xpath('//a[contains(text(), "E-Mail")]/@href').string()
    if author_url and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="testreviewContent"]//@alt').string()
    if grade_overall:
        grade_overall = grade_overall.split()[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//table[@class="fontSite18"]/tr')
    for grade in grades:
        grade_name = grade.xpath('td[1]/text()').string()
        grade_val = grade.xpath('.//@src').string().split('-')[-1].replace('.png', '')
        if grade_val.isdigit():
            grade_val = float(grade_val) / 2
            review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    summary = data.xpath('//p[@class="introduction"]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//h2[@class="deviceHeadline"]//text()').string(multiple=True)

    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Fazit")]/following-sibling::text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace('Fazit:', '').replace('Fazit ', '')
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Fazit")]/preceding-sibling::p[not(@class)]//text()|//h3[contains(., "Fazit")]/preceding-sibling::text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="block-testbericht"]/p[not(@class)]//text()|//div[@id="block-testbericht"]/text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
