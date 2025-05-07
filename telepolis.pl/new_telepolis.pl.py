from agent import *
from models.products import *
import simplejson
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.telepolis.pl/api/infinity-content/artykuly/testy-sprzetu?page=1', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    data_json = simplejson.loads(data.content)

    new_data = data.parse_fragment(data_json.get('contents'))
    revs = new_data.xpath('//a[contains(@class, "teaser--mobile")]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(url=url))

    has_next_page = data_json.get('hasNextPage')
    if has_next_page:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.telepolis.pl/api/infinity-content/artykuly/testy-sprzetu?page=' + str(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    title = data.xpath('//h1[contains(@class, "title")]/text()').string()

    product = Product()
    product.name = title.replace('(pierwsze wrażenia)', '').replace('(test)', '').replace('(Test)', '').replace('- test', '').replace('(albo zazdrosna)', '').split('. Test ')[-1].split('? Test ')[-1].replace('. Test', '').strip()
    product.ssid = context['url'].split('/')[-1].replace('testy-', '').replace('-test', '')
    product.category = 'Technologia'

    product.url = data.xpath('//a[@class="sales-item"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid

    revs_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if revs_json:
        revs_json = simplejson.loads(revs_json)

        date = revs_json.get('datePublished')
        if date:
            review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "date__name")]/text()').string()
    if author:
        author = author.title()
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('(//h3[contains(., "Ocena końcowa:")]|//span[contains(@class, "review__title")])//text()[regexp:test(., "\d+,?\d?/\d+")]').string(multiple=True)
    if not grade_overall:
        grade_overall = data.xpath('//strong[contains(., "ocena końcowa")]/text()[regexp:test(., "\d+,?\d?/\d+")]').string()

    if grade_overall:
        grade_overall = re.search(r'\d+,?\d?/\d+', grade_overall).group().split('/')[0].replace(',', '.')
        if len(grade_overall) > 1 and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value= float(grade_overall), best=10.0))

    grades = data.xpath('//div[contains(., "Ocena końcowa:")]/following-sibling::div[contains(@class, "paragraph")][1][regexp:test(., "\d+,?\d?/\d+")]//li')
    for grade in grades:
        grade = grade.xpath('.//text()').string(multiple=True)
        if grade:
            grade_name, grade_val = grade.split(':') if ':' in grade else grade.split(', ')
            grade_val = grade_val.split('/')[0].replace(',', '.')
            grade_name = grade_name.strip()
            if len(grade_val) > 1 and float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('(//div[contains(., "Zalety:")]/following-sibling::div[contains(@class, "paragraph")][1][not(contains(., "Wady:"))]//p|//div[contains(., "Zalety:")]/following-sibling::div[contains(@class, "paragraph")][1][not(contains(., "Wady:"))]//li)//text()[not(contains(., "Zalety:"))][normalize-space(.)]')
    if not pros:
        pros = data.xpath('//div[contains(@class, "review__content") and contains(., "plusy")]//li/div[not(@class)]//text()[normalize-space(.)]')
    if not pros:
        pros = data.xpath('//p[contains(., "Zalety:")]/text()[not(regexp:test(., "Zalety:|Wady:"))][normalize-space(.)]')

    for pro in pros:
        pro = pro.string().strip(' \n+-.,')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('(//div[contains(., "Wady:")]/following-sibling::div[contains(@class, "paragraph")][1]//p|//div[contains(., "Wady:")]/following-sibling::div[contains(@class, "paragraph")][1]//li)//text()[not(contains(., "Wady:"))][normalize-space(.)]')
    if not cons:
        cons = data.xpath('//div[contains(@class, "review__content") and contains(., "minusy")]//li/div[not(@class)]//text()[normalize-space(.)]')
    if not cons:
        cons = data.xpath('//p[contains(., "Wady:")]/text()[not(regexp:test(., "Zalety:|Wady:"))][normalize-space(.)]')

    for con in cons:
        con = con.string().strip(' \n+-.,')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="article__lead"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[regexp:test(., "Podsumowanie|Dla kogo to produkt?")]/following-sibling::div/p[not(preceding::div[regexp:test(., "Wady:|Zalety:")] or regexp:test(., "Wady:|Zalety:"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[regexp:test(., "Podsumowanie|Dla kogo to produkt?")]/preceding-sibling::div/p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content")]/p[not(preceding::div[regexp:test(., "Wady:|Zalety:")] or regexp:test(., "Wady:|Zalety:"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
