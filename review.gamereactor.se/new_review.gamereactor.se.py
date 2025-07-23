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
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request('https://www.gamereactor.se/recensioner/', use='curl', force_charset='utf-8'), process_revlist, dict())
    session.queue(Request('http://www.gamereactor.se/hardvara/', use="curl"), process_revlist, dict(cat='Hårdvara'))
    session.queue(Request('http://www.gamereactor.se/blu-ray/', use="curl"), process_revlist, dict(cat='Blu-ray'))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//article[@class="areview"]/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.url = context['url']
    product.ssid = data.xpath('//article/@data-id').string()
    product.manufacturer = data.xpath('//li[span[contains(., "Utvecklare:")]]//text()[not(parent::span)]').string(multiple=True)

    title = data.xpath('//h1/text()').string()
    product.name = data.xpath('//section[contains(@class, "gameinfo")]/h2/a/text()').string()
    if not product.name:
        product.name = title

    product.category = context.get('cat')
    if not product.category:
        product.category = 'Spel'

        platforms = data.xpath('//li[span[regexp:test(., "Testat på:|Finns även till:")]]/text()[normalize-space(.)]').join('/')
        if platforms:
            product.category += '|' + platforms.replace(', ', '/')

        genres = data.xpath('//li[span[contains(., "Genre:")]]/a/text()').join('/')
        if genres:
            product.category += '|' + genres

    product.category = product.category.replace('/ ', '/').strip()

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@itemprop="datePublished"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//li[contains(@class, "publishAuthor")]//a//text()').string(multiple=True)
    author_url = data.xpath('//li[contains(@class, "publishAuthor")]//a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('=')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="scoreSplit"]//meter/@value').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pro = data.xpath('//div[@class="goodbad"][preceding-sibling::div[contains(., "+")]][1]/text()').string()
    if pro:
        pro = re.sub(r'<.*?>', '', pro)
        review.add_property(type='pros', value=pro)

    con = data.xpath('//div[@class="goodbad"][preceding-sibling::div[contains(., "-")]][1]/text()').string()
    if con:
        con = re.sub(r'<.*?>', '', con)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[@itemprop="alternativeHeadline"]/text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@id="page0"]/p//text()').string(multiple=True)
    if excerpt:
        excerpt = re.sub(r'<.*?>', '', excerpt).replace('<bild<', '').replace('" target="_blank">', '').replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
