from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://fifahungary.co.hu/leiras_tesztarc.php', use='curl'), process_revlist, {})


def process_revlist(data, context, session):
    for rev in data.xpath("//table[@class='dotted']/tbody/tr/td[1]//a[regexp:test(@href,'fifahungary')]"):
        url = rev.xpath("@href").string()
        name = rev.xpath("text()").string(multiple=True)
        session.queue(Request(url, use='curl'), process_review, dict(url=url, name=name))


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.manufacturer = data.xpath('//p[contains(., "ejlesztő:")]/following-sibling::p[1]/text()').string()

    platform = data.xpath('//li[contains(.,"Tesztplatform")]/text()').string()
    if platform:
        product.category = "Games|" + platform
    else:
        product.category = "Games"

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//p[contains(., "megjelenés:")]/following-sibling::p[1]/text()').string()

    author = data.xpath('//li[contains(., "Írta:")]/a[contains(@href, "szemelylap.php")]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_img = data.xpath('//img[contains(@src, "images/ertekeles/")]/@src')
    grade_overall = ''
    for grade in grade_img:
        grade_overall += grade.string().rsplit('.', 1)[0][-1]

    if grade_overall and grade_overall.isdigit():
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grade_names = ['Grafika', 'Játékmenet', 'Tartalom', 'Zene', 'Szavatosság']
    grades = data.xpath('//table[@class="ertekeles"]/tr/td')
    for grade_name, grade in zip(grade_names, grades):
        grade_value = grade.xpath('text()').string()
        if grade_value and grade_value.isdigit():
            review.grades.append(Grade(name=grade_name, value=float(grade_value), best=100.0))

    pros = data.xpath('//div[@class="ert-pro"]//div')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' +-*.')
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="ert-kontra"]//div')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(' +-*.')
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="bevezeto"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//*[regexp:test(text(), "ÖSSZEGZÉS|Végeredmény|ÉRZÉS|Összkép")]/following::div[@align="justify"]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//*[regexp:test(text(), "ÖSSZEGZÉS|Végeredmény|ÉRZÉS|Összkép")]/preceding-sibling::div//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="teszt"]/*[not(regexp:test(., "rendezte:|Közremüködött:"))]//text()').string(multiple=True)

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
