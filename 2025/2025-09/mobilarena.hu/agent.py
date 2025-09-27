from agent import *
from models.products import *


XCAT = ['Tudástár']


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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://mobilarena.hu/tesztek/index.html', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="content-filter-option"]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h4/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' - ')[0].split(' – ')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat'].replace('Egyéb', 'Technika')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@itemprop="author"]//text()').string(multiple=True)
    author_url = data.xpath('//a[@itemprop="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].replace('.html', '')
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grades = data.xpath('//tr[td[contains(text(), "pont")]]')
    for grade in grades:
        grade_name = grade.xpath('th//text()').string()
        grade_val = grade.xpath('td/text()').string()
        if grade_name and grade_val:
            grade_val = float(grade_val.replace('pont', '').split('/')[0].replace(',', '.'))
            review.grades.append(Grade(name=grade_name, value=grade_val, best=10.0))

    if not grades:
        grades = data.xpath('//tbody[tr/td[contains(text(), "pont")]]/tr[not(@class)]')
        if grades and len(grades) == 2:
            grades_name, grades_val = grades
            for grade_name, grade_val in zip(grades_name, grades_val):
                grade_name = grade_name.xpath('.//text()').string(multiple=True)
                grade_val = grade_val.xpath('.//text()').string(multiple=True)
                if 'pont' in grade_val and grade_name:
                    grade_val = float(grade_val.replace('pont', '').split('/')[0].replace(',', '.'))
                    review.grades.append(Grade(name=grade_name, value=grade_val, best=10.0))

    pros = data.xpath('//tr[contains(@class, "subhead-pro")]/following-sibling::tr[not(@class or preceding-sibling::tr[contains(@class, "subhead-con")])]/th')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//tr[contains(@class, "subhead-con")]/following-sibling::tr/th')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@itemprop="description about"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[regexp:test(., "Verdikt|Összegzés")]/following-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[b[regexp:test(text(), "Verdikt|Összegzés")]]/following-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[regexp:test(., "Verdikt|Összegzés")]/preceding-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[b[regexp:test(text(), "Verdikt|Összegzés")]]/preceding-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="content-body"]/p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)

    next_page = data.xpath('//a[@rel="next"]/@href').string()
    if next_page:
        pages = data.xpath('(//div[contains(@class, "dropdown-menu-limit")])[1]/a[@class="dropdown-item"]')
        for page in pages:
            title = page.xpath('text()').string()
            page_url = page.xpath('@href').string()
            review.add_property(type='pages', value=dict(title=title, url=page_url))

        session.do(Request(next_page, use='curl', force_charset='utf-8', max_age=0), process_review_next, dict(excerpt=excerpt, review=review, product=product))

    elif excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_next(data, context, session):
    strip_namespace(data)

    next_page = data.xpath('//a[@rel="next"]/@href').string()
    if next_page and next_page == data.response_url:
        next_page = next_page.replace('mobilarena.hu', 'prohardver.hu')
        session.do(Request(next_page, use='curl', force_charset='utf-8', max_age=0), process_review_next, dict(context))
        return

    review = context['review']

    grades = data.xpath('//tr[td[contains(text(), "pont")]]')
    for grade in grades:
        grade_name = grade.xpath('th//text()').string()
        grade_val = grade.xpath('td/text()').string()
        if grade_name and grade_val:
            grade_val = float(grade_val.replace('pont', '').split('/')[0].replace(',', '.'))
            review.grades.append(Grade(name=grade_name, value=grade_val, best=10.0))

    if not grades:
        grades = data.xpath('//tbody[tr/td[contains(text(), "pont")]]/tr[not(@class)]')
        if grades and len(grades) == 2:
            grades_name, grades_val = grades
            for grade_name, grade_val in zip(grades_name, grades_val):
                grade_name = grade_name.xpath('.//text()').string(multiple=True)
                grade_val = grade_val.xpath('.//text()').string(multiple=True)
                if 'pont' in grade_val and grade_name:
                    grade_val = float(grade_val.replace('pont', '').split('/')[0].replace(',', '.'))
                    review.grades.append(Grade(name=grade_name, value=grade_val, best=10.0))

    pros = data.xpath('//tr[contains(@class, "subhead-pro")]/following-sibling::tr[not(@class or preceding-sibling::tr[contains(@class, "subhead-con")])]/th')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//tr[contains(@class, "subhead-con")]/following-sibling::tr/th')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h3[regexp:test(., "Verdikt|Összegzés")]/following-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[b[regexp:test(text(), "Verdikt|Összegzés")]]/following-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[regexp:test(., "Verdikt|Összegzés")]/preceding-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[b[regexp:test(text(), "Verdikt|Összegzés")]]/preceding-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not excerpt and not conclusion:
        excerpt = data.xpath('//div[@class="content-body"]/p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)

    if excerpt:
        context['excerpt'] += '' + excerpt

    next_page = data.xpath('//a[@rel="next"]/@href').string()
    if next_page:
        if next_page == data.response_url:
            next_page = next_page.replace('mobilarena.hu', 'prohardver.hu')

        session.do(Request(next_page, use='curl', force_charset='utf-8', max_age=0), process_review_next, dict(context, review=review))

    elif context['excerpt']:
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
