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
    session.sessionbreakers = [SessionBreak(max_requests=9000)]
    session.queue(Request('https://www.gamesaktuell.de/Artikel-Archiv/Tests/', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict())
    session.queue(Request('https://www.gamesaktuell.de/Artikel-Archiv/Tests/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="cal_years"]/a/@href')
    for cat in cats:
        url = cat.string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "lpPagination_right")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = data.xpath('//span[contains(@class, "productTitle")]//text()').string(multiple=True) or re.sub(r'\(.+\)', '', context['title']).split(' im Test')[0].replace('Test/Review: ', '').replace('Review: ', '').strip()
    product.ssid = context['url'].split('/')[-2].split('-')[-1]
    product.category = 'Technik'

    platforms = data.xpath('//ul[@id="productNavigation"]//button/text()').join('/')
    if platforms:
        product.category =  'Spiele|' + platforms

    product.url = data.xpath('//a[.//button[contains(., "ZUM ANGEBOT")]]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[@class="articleTitle"]/text()').string()
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//span[contains(@class, "date")]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "authors")]//span[@class="authorName"]/text()').string()
    author_url = data.xpath('//span[contains(@class, "authors")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('=')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="ratingData"]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.replace(',', '.')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[div/span[contains(text(), "Pro & Contra")]]//span[contains(@class, "ratingPro")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[div/span[contains(text(), "Pro & Contra")]]//span[contains(@class, "ratingContra")]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[contains(@class, "artIntro")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[contains(@class, "rating")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "rating")]/preceding-sibling::p[not(contains(., "Test-Update vom"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="textContainer"]/p//text()').string(multiple=True)

    next_url = data.xpath('//a[@title="Nächste Seite"]/@href').string()
    if next_url:
        title = review.title + ' - Pagina 1'
        review.add_property(type='pages', value=dict(title=title, url=data.response_url))
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(excerpt=excerpt, review=review, product=product))

    elif excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_next(data, context, session):
    strip_namespace(data)

    review = context['review']

    page =context.get('page', 2)
    title = review.title + ' - Pagina ' + str(page)
    review.add_property(type='pages', value=dict(title=title, url=data.response_url))

    grade_overall = data.xpath('//span[@class="ratingData"]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.replace(',', '.')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[div/span[contains(text(), "Pro & Contra")]]//span[contains(@class, "ratingPro")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[div/span[contains(text(), "Pro & Contra")]]//span[contains(@class, "ratingContra")]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[contains(@class, "rating")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "rating")]/preceding-sibling::p[not(contains(., "Test-Update vom"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="textContainer"]/p//text()').string(multiple=True)

    if excerpt:
        context['excerpt'] += ' ' + excerpt

    next_url = data.xpath('//a[@title="Nächste Seite"]/@href').string()
    if next_url:
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context, review=review, page=page+1))

    elif context['excerpt']:
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
