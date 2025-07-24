from agent import *
from models.products import *


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
    session.queue(Request('http://www.splashgames.de/php/rezensionen/alle', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//tr[td[@class="tabelleninhalt" and contains(@style, "cursor")] and not(td[@class="tabellenueberschrift"])]/td/a[not(contains(@href, "/rezensionen/kategorie"))]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(text(), ">>")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.manufacturer = data.xpath('//b[contains(., "Entwickler:")]/following-sibling::a[1]/text()').string()
    product.category = 'Spiele'

    platforms = data.xpath('//b[contains(., "Systeme:")]/following-sibling::text()[1]').string()
    if platforms:
        product.category += '|' + platforms.replace(', ', '/')

    genre = data.xpath('//b[contains(., "Genre:")]/following-sibling::a[1]/text()').string()
    if genre:
        product.category += '|' + genre

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//tr[td[contains(., "Rezension vom:")]]/td[not(contains(., "Rezension vom:"))]/text()').string()

    author = data.xpath('//td[contains(., "Autor der Besprechung:")]/a[@target="_top"]/text()').string()
    author_url = data.xpath('//td[contains(., "Autor der Besprechung:")]/a[@target="_top"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//img[contains(@alt, "Wertung:")]/@alt').string()
    if grade_overall:
        grade_overall = float(grade_overall.split(':')[-1].split('.')[0].strip(' :.'))
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    grades = data.xpath('//td[img[contains(@alt, "Wertung:")]]/text()[not(contains(., "Wertung:"))][normalize-space(.)]')
    for grade in grades:
        grade_name, grade_val = grade.string().split(':')
        grade_val = float(grade_val.strip(' :.'))
        if grade_val:
            best = 10.0
            if grade_val > 10:
                best = float(int(grade_val) + 1)

            review.grades.append(Grade(name=grade_name, value=grade_val, best=best))

    pros = data.xpath('((//tbody[tr/td/img[@alt="Pluspunkte"]]/tr)[2]/td)[2]//li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('((//tbody[tr/td/img[@alt="Minuspunkte"]]/tr)[2]/td)[3]//li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//b[contains(., "Fazit:")]/following-sibling::text()|//b[contains(., "Fazit:")]/following-sibling::*[not(self::b)]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').replace('�', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//b[contains(., "Inhalt:")]/following-sibling::text()|//b[contains(., "Inhalt:")]/following-sibling::*[not(preceding-sibling::b[contains(., "Fazit:")] or self::b)]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').replace('�', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
