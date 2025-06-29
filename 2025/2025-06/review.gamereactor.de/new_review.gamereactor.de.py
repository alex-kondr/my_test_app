from agent import *
from models.products import *


XCAT = ["Buyer's guide"]


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
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.gamereactor.de/', use='curl', force_charset='utf-8'), process_frontpage, dict())
    session.queue(Request('https://www.gamereactor.de/Kritiken/', use='curl', force_charset='utf-8'), process_revlist, dict())
    session.queue(Request('https://www.gamereactor.de/Film/', use='curl', force_charset='utf-8'), process_revlist, dict(cat='Film'))
    session.queue(Request('https://www.gamereactor.de/series/', use='curl', force_charset='utf-8'), process_revlist, dict(cat='Series'))


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[a[contains(., "Hardware")]]//div[@class="subMenuBlock"]/a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_revlist, dict(cata='Hardware|' + name))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//a[h2]')
    for rev in revs:
        title = rev.xpath('h2/text()').string()
        url = rev.xpath('@href').string()

        if title and url:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace(' Testbericht', '').replace(' Hardware-Review', '').replace(' - Multiplayer-Review', '').split(' Review')[0].replace(' im Dauertest', '').strip(' +-.')
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.manufacturer = data.xpath('//li[regexp:test(., "Verleih:|Entwickler:|Hersteller:")]//text()[not(regexp:test(., "Verleih:|Entwickler:|Hersteller:"))]').string(multiple=True)

    category = context.get('cat', '')

    platforme = data.xpath('//li[regexp:test(., "Gespielt auf:|Kategorie:")]//text()[not(regexp:test(., "Gespielt auf:|Kategorie:"))]').string(multiple=True)
    if platforme:
        category += '|' + platforme.replace(', ', '/')

    genre = data.xpath('//li[contains(., "Genre:")]//text()[not(contains(., "Genre:"))]').string(multiple=True)
    if genre:
        category += '|' + genre.replace(', ', '/')

    product.category = category.strip(' |,').replace(' /', '/')
    if not product.category:
        product.category = 'Technik'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@itemprop="datePublished"]/@content').string()
    if not date:
        date = data.xpath('//li[@class="publishDateTime bullet"]/time/@datetime').string()

    if date:
        review.date = date.split('CE')[0]

    author = data.xpath('//li[@class="publishAuthor bullet"]//a/text()').string()
    author_url = data.xpath('//li[@class="publishAuthor bullet"]//a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('=')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="bigScoreWrapper"]//img/@alt').string()
    if grade_overall and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pro = data.xpath('(//div[@class="goodbadheader" and normalize-space(text())="+"]/following-sibling::div[@class="goodbad"])[1]//text()').string(multiple=True)
    if pro:
        pro = pro.strip(' +-*.;•–')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    con = data.xpath('(//div[@class="goodbadheader" and normalize-space(text())="-"]/following-sibling::div[@class="goodbad"])[1]//text()').string(multiple=True)
    if con:
        con = con.strip(' +-*.;•–')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[@class="intro"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[contains(@id, "page")]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
