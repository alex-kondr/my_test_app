from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('http://www.foto-video.ru/tech/test/', use='curl', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//p[contains(@class, "news-item")]/a')
    for rev in revs:
        title = rev.xpath('.//text()').string(multiple=True)
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//div[@class="numbers"]/a[contains(., "»")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Photo and Video'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//div[@class="preview"]/p/text()').string()

    author = data.xpath('//div/text()[contains(., "Тест")]/following-sibling::b[1]/text()').string(multiple=True)
    if not author:
        author = data.xpath('//div/text()[contains(., "Текст ")]/following-sibling::b[1]/text()').string()

    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//tr[td[contains(., "Общая оценка")]]/td[not(contains(., "Общая оценка"))]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.replace(',', '.')
        if '*' in grade_overall:
            grade_overall = grade_overall.count('*')
            if float(grade_overall) > 0:
                review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    grades = data.xpath('//tbody[tr[contains(., "Общая оценка")]]/tr[td[regexp:test(., "\d+")] and not(contains(., "Общая оценка"))]')
    for grade in grades:
        grade_name = grade.xpath('td/b/text()').string()
        grade_val = grade.xpath('td[not(b)]/text()').string()
        if grade_name and grade_val and float(grade_val) > 0:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    if not grades or not grade_name:
        grades = data.xpath('//tr[td[contains(text(), "*")] and not(td[contains(text(), "Общая оценка")])]')
        for grade in grades:
            grade_name = grade.xpath('td[not(contains(text(), "*"))]/text()').string()
            grade_val = grade.xpath('td[contains(text(), "*")]/text()').string()
            if grade_name and grade_val:
                grade_val = grade_val.count('*')
                if float(grade_val) > 0:
                    review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('//tr[td[b[contains(text(), "Плюсы:")]]]/td[not(contains(., "Плюсы:"))]//text()[normalize-space(.)]')
    if not pros:
        pros = data.xpath('//b[contains(., "Достоинства:")]/following-sibling::text()[1]')
    if not pros:
        pros = data.xpath('//div[@class="preview"]/text()[contains(., "Достоинства:")]')
    if not pros:
        pros = data.xpath('//b[contains(text(), "Плюсы:")]/following-sibling::text()[1]')
    if not pros:
        pros = data.xpath('//tr[td[contains(text(), "Плюсы")]]/td[not(contains(., "Плюсы"))]//text()[normalize-space(.)]')

    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.replace('Достоинства:', '').strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//tr[td[b[contains(text(), "Минусы:")]]]/td[not(contains(., "Минусы:"))]//text()[normalize-space(.)]')
    if not cons:
        cons = data.xpath('//b[contains(., "Недостатки:")]/following-sibling::text()[1]')
    if not cons:
         cons = data.xpath('//div[@class="preview"]/text()[contains(., "Недостатки:")]')
    if not cons:
        cons = data.xpath('//b[contains(text(), "Минусы:")]/following-sibling::text()[1]')
    if not cons:
        cons = data.xpath('//tr[td[contains(text(), "Минусы")]]/td[not(contains(., "Минусы"))]//text()[normalize-space(.)]')

    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.replace('Недостатки:', '').strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="preview" and not(regexp:test(., "Достоинства:|Недостатки:"))]/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    image = data.xpath('//div[@id="photo_img"]/a/@href').string()
    if image:
        product.add_property(type="image", value=dict(type='product', src=image))

    images = data.xpath('//a[img[@class="preview-pic" and regexp:test(@alt, "\D+")]]')
    for image in images:
        image_src = image.xpath('@href').string()
        image_alt = image.xpath('.//@alt').string()
        product.add_property(type="image", value=dict(src=image_src, alt=image_alt))

    excerpt = data.xpath('(//div[text()[contains(., "Тест ")]]/text()[not(contains(., "Тест "))]|//div[text()[contains(., "Тест ")]]/p//text())[not(contains(., "Полные тексты статей читайте в"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//div[text()[contains(., "Текст ")]]/text()[not(contains(., "Текст "))]|//div[text()[contains(., "Текст ")]]/p//text())[not(contains(., "Полные тексты статей читайте в"))]').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
