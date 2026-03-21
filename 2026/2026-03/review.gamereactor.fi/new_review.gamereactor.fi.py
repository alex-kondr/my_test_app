import re
from agent import *
from models.products import *
import HTMLParser


h = HTMLParser.HTMLParser()


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
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request('http://www.gamereactor.fi/arviot/', max_age=0), process_revlist, dict(cat='Pelit'))
    session.queue(Request('http://www.gamereactor.fi/laitteet/', max_age=0), process_revlist, dict(cat='Laitteet'))
    session.queue(Request('http://www.gamereactor.fi/elokuvat/', max_age=0), process_revlist, dict(cat='Elokuvat'))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//article[@class="areview"]/a')
    for rev in revs:
        title = rev.xpath("h2/text()").string()
        url = rev.xpath('@href').string()

        if '(REVIEW REMOVED)' not in title.upper():
            session.queue(Request(url, max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href ').string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.url = context['url']
    product.ssid = data.xpath('//article/@data-id').string()

    product.name = data.xpath('//section[contains(@class, "gameinfo")]/h2/a/text()').string()
    if not product.name:
        product.name = context['title']

    product.category = context['cat']
    platforms = data.xpath('//li[span[contains(., "Testattu:") or contains(., "Yhteensopiva:")]]/text()').string(multiple=True)
    if platforms:
        product.category += '|' + '/'.join([platform.strip() for platform in platforms.split(',') if platform.strip()])

    genres = data.xpath('//li[span[contains(., "Pelityyppi:")]]//text()[not(parent::span)]').string(multiple=True)
    if genres:
        product.category += '|' + '/'.join([genre.strip() for genre in genres.split(',') if genre.strip()])

    product.manufacturer = data.xpath('//li[span[contains(., "Valmistaja:") or contains(., "Kehittäjä:") or contains(., "Elokuvayhtiö:")]]//text()[not(parent::span)]').string(multiple=True)
    if not product.manufacturer:
        product.manufacturer = data.xpath('//li[span[contains(., "Julkaisija:")]]//text()[not(parent::span)]').string(multiple=True)

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@itemprop="datePublished"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//li[contains(@class, "publishAuthor")]//a').first()
    if author:
        author_name = author.xpath('.//text()').string().split('(Käännös:')[0].strip()
        review.authors.append(Person(name=author_name, ssid=author_name))

    grade_overall = data.xpath('//div[@class="scoreSplit"]//meter/@value').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pro = data.xpath('//div[@class="goodbad"][preceding-sibling::div[contains(., "+")]][1]/text()').string()
    if pro:
        pro = pro.strip(' +-*.:;•,–')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    con = data.xpath('//div[@class="goodbad"][preceding-sibling::div[contains(., "-")]][1]/text()').string()
    if con:
        con = con.strip(' +-*.:;•,–')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[@itemprop="alternativeHeadline"]/text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@id="page0"]/p//text()').string(multiple=True)
    if excerpt:
        excerpt = re.sub(r'<.*?>', '', h.unescape(excerpt).replace('<b<', '').replace('&#269;', 'č').replace('&#263;', 'ć'))
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
