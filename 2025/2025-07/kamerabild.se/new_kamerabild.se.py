from agent import *
from models.products import *
import re


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.kamerabild.se/tagg/tester', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//div[@class="content"]/a')
    for rev in revs:
        title = rev.xpath('.//h2/text()').string()
        url = rev.xpath('@href').string()

        if not re.search(r'Lista: |Bästa mobilkameran|bästa kamera|Mobilkameratest |Jämförelse: ', title, flags=re.I|re.U):
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

# no next page


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('TEST: ', '').replace('Test: ', '').replace('Vi testar ', '').split(' – ')[0].split(': TEST')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = 'Kamera'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]//text()').string(multiple=True)
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.replace('mailto:', '').split('@')[0]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//*[regexp:test(text(), "TOTALT: \d")]//text()').string()
    if not grade_overall:
        grade_overall = data.xpath('//p[regexp:test(., "TOTALT: \d")]//text()').string(multiple=True)

    if grade_overall:
        grade_overall = float(grade_overall.split()[-1].replace(',', '.'))
        best = 100.0 if grade_overall > 5 else 5.0
        review.grades.append(Grade(type='overall', value=grade_overall, best=best))

    grades = data.xpath('//h3[contains(text(), "Betyg")]/following-sibling::p[not(contains(., "TOTALT:"))]/text()[contains(., ": ")]')
    if not grades:
        grades = data.xpath('//h2[contains(text(), "Betyg")]/following-sibling::p[1][contains(., ":")]/text()')

    for grade in grades:
        grade_name, grade_val = grade.string().split(':')
        grade_val = float(grade_val.replace(',', '.'))
        best = 100.0 if grade_val > 5 else 5.0
        review.grades.append(Grade(name=grade_name, value=grade_val, best=best))

    if not grades:
        grades = data.xpath('//h3[contains(text(), "Betyg")]/following-sibling::p[@class="no-indent" and contains(., ":") and not(contains(., "TOTALT"))]')
        for grade in grades:
            grade_name, grade_val = grade.xpath('.//text()').string(multiple=True).split(':')
            grade_val = float(grade_val.replace(',', '.'))
            best = 100.0 if grade_val > 5 else 5.0
            review.grades.append(Grade(name=grade_name, value=grade_val, best=best))

    pros = data.xpath('//h2[contains(text(), "Plus")]/following-sibling::div/p/text()')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//h2[contains(text(), "Minus")]/following-sibling::div/p/text()')
    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[contains(@class, "subtitle")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h3|//h2)[contains(text(), "Slutsats")]/following-sibling::p[not(@class or preceding::h3[contains(text(), "Betyg")] or preceding::h2[contains(text(), "Betyg")])]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h3|//h2)[contains(text(), "Slutsats")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "bodytext")]/p[not(@class or preceding::h3[contains(text(), "Betyg")] or preceding::h2[contains(text(), "Betyg")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
