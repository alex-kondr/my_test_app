from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('http://www.bigscreen.se/tester/tester-ant.htm'), process_prodlist, dict())
    session.queue(Request('http://www.bigscreen.se/tester/tester-aot.htm'), process_prodlist, dict())


def process_prodlist(data, context, session):
    revs = data.xpath('//p/a[@target="scrn"]')
    for rev in revs:
        name = rev.xpath('text()').string(multiple=True)
        url = rev.xpath('@href').string()

        if name and  url:
            session.queue(Request(url), process_product, dict(name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = data.xpath('//p[@class="KapRub"]/text()[normalize-space(.)]').string() or context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.htm', '')
    product.category = 'Hemma bio'

    cat = data.xpath('//i[contains(., "projektortest")]/text()').string()
    if cat:
        product.category += '|' + cat.split(',')[-2].strip().title()

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//p[@class="bigRubTester"]//text()').string(multiple=True)
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//i[contains(., "projektortest")]/text()').string()
    if date:
        review.date = date.split(',')[-1].strip()

    grade_overall = data.xpath('//font[regexp:test(normalize-space(text()), "^\d+/\d+$")]/text()').string()
    if grade_overall:
        grade_overall, grade_best = grade_overall.split('/')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=float(grade_best)))

    grades_names = data.xpath('(//p[span[contains(., "BETYG")]]/font)[1]//text()[normalize-space(.)]').strings()
    grades = data.xpath('(//p[font[contains(text(), "O")]])[1]/font/text()').strings()
    for grade_name, grade_val in zip(grades_names, grades):
        grade_name = grade_name.strip(' +-*:;\n\t')
        grade_val = grade_val.count('O')
        if grade_name and grade_val > 0:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('(//p|//td)[span[contains(., "PLUS")]]/font//text()[contains(., "+")]')
    for pro in pros:
        pro = pro.string().strip(' +-.*')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p|//td)[span[contains(., "MINUS")]]//font//text()[contains(., "-")]')
    for con in cons:
        con = con.string().strip(' +-*.')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="ingress"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[span[contains(., "OMDÖME")]]//font[not(contains(., "OMDÖME"))]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace('\n', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//p[not(@class or @align)]|//p[not(@class or @align)]/strong)/text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
