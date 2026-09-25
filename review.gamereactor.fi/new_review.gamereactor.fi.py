from agent import *
from models.products import *
import re
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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=9000)]
    session.queue(Request('http://www.gamereactor.fi/arviot/'), process_revlist, dict(cat='Pelit'))
    session.queue(Request('http://www.gamereactor.fi/laitteet/'), process_revlist, dict(cat='Laitteet'))
    session.queue(Request('http://www.gamereactor.fi/elokuvat/'), process_revlist, dict(cat='Elokuvat'))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('(//main[@id="main-content"]/div/a|//a[contains(@class, "gn-story") or contains(@class, "gn-dayrow")])/@href')
    for rev in revs:
        url = rev.string()
        session.queue(Request(url), process_review, dict(url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())

def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.url = context['url']
    product.ssid = data.xpath('//article/@data-id').string()
    product.category = 'Juegos'
    product.manufacturer = data.xpath('//div[contains(@class, "side-sticky")]//div[contains(span, "Kehittäjä")]/span[not(contains(., "Kehittäjä"))]/text()').string(multiple=True)

    title = data.xpath("//h1/text()").string()
    product.name = data.xpath('//div[@class="gr-headgrid"]//div[normalize-space(span/text())="Arviot"]/span[not(contains(., "Arviot"))]/text()').string()
    if not product.name:
        product.name = title.replace('Análisis de ', '').replace('...', '').strip()

    platforms = data.xpath('//div[contains(span, "Alustat")]/div/span/text()').join('/')
    if platforms:
        product.category += '|' + platforms

    genres = data.xpath('//div[contains(@class, "side-sticky")]//div[contains(span, "Pelityyppi")]/span[not(contains(., "Pelityyppi"))]/text()').join('/')
    if genres:
        product.category += '|' + genres

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "revbyline") or contains(@class, "headgrid")]//a[contains(@href, "/author/")]//text()').string(multiple=True)
    author_url = data.xpath('//div[contains(@class, "revbyline") or contains(@class, "headgrid")]//a[contains(@href, "/author/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "side-sticky")]/div/div/span/text()[regexp:test(., "^\d{1,2}$")]').string()
    if not grade_overall:
        grade_overall = data.xpath('//div[contains(@class, "gr-verdict")]/div/div/span/text()[regexp:test(., "^\d{1,2}$")]').string()

    if grade_overall and grade_overall.isdigit() and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[contains(@class, "gr-verdict")]//div[contains(span, "Plussat")]/span[not(contains(., "Plussat"))]/text()')
    for pro in pros:
        pro = pro.string()
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "gr-verdict")]//div[contains(span, "Miinukset")]/span[not(contains(., "Miinukset"))]/text()')
    for con in cons:
        con = con.string()
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[div/h1]/div[not(a)]/span//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[contains(@class, "gr-verdict")]/div/p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@id="page0"]/p//text()').string(multiple=True)
    if excerpt:
        excerpt = re.sub(r'<.*?>', '', h.unescape(excerpt)).replace('<bild<', '').replace('" target="_blank">', '').replace(u'\uFEFF', '').replace('&#363;', u'ū').replace('&#333;', u'ō').replace('<b<', '').replace('&#269;', 'č').replace('&#263;', 'ć').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
