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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.nexgam.de/Datenbank?Tags=Reviews', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = re.sub(r' im.+Review| im Test| [P]?review[s]?|\[.+\] neXGam:|\[.+\]|\(.+\)', '', context['title'], flags=re.I|re.U).strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = 'Spiele'

    manufacturer = data.xpath('//tr[contains(., "Vermarkter")]/td[not(contains(., "Vermarkter"))]/text()').string()
    if manufacturer and manufacturer.strip(' +-*.:;•–'):
        product.manufacturer = manufacturer.strip(' +-*.:;•–')

    platforms = data.xpath('//img[contains(@src, "https://www.nexgam.de/media/cache/nexgam/consoles/")]/@title').join('/')
    if platforms:
        product.category += '|' + platforms

    genres = data.xpath('//tr[contains(., "Genre")]/td[not(contains(., "Genre"))]/text()').string()
    if genres:
        product.category += '|' + genres.replace(', ', '/')

    product.category = product.category.strip(' +-*.:;•–|')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//time[@itemprop="datePublished"]/@datetime').string()

    author = data.xpath('//h2[@class="fazit-userh2"]/text()').string()
    if author:
        author = author.replace('meint:', '').strip()
        if author:
            review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="rating green"]//text()').string(multiple=True)
    if grade_overall:
        try:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))
        except:
            pass

    grade_user = data.xpath('//span[@class="user-rating-box-rating-sum green"]/text()').string()
    if grade_user:
        review.grades.append(Grade(name='Userwertung', value=float(grade_user), best=10.0))

    pros = data.xpath('//ul[@class="positiv"]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="negativ"]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//section[@class="review-short"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[@class="user-comment"]/p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//section[@class="review-content"]//text()').string(multiple=True)
    if excerpt:
        if 'Mein Fazit:' in excerpt:
            excerpt, conclusion = excerpt.rsplit('Mein Fazit:', 1)
            review.add_property(type='conclusion', value=conclusion.strip())
        elif 'Fazit:' in excerpt and not conclusion:
            excerpt, conclusion = excerpt.rsplit('Fazit:', 1)
            review.add_property(type='conclusion', value=conclusion.strip())

        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
