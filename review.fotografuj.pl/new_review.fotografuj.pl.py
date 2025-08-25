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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.fotografuj.pl/Dzial/Testy_praktyczne', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//td[@class="intro"]/a')
    for rev in revs:
        title = rev.xpath('.//text()').string(multiple=True)
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(text(), "następna strona")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' – ')[0].replace('TEST: ', '').replace(u'\uFEFF', '').strip()
    product.ssid = context['url'].split('/')[-1]
    product.category = 'Technologia'

    product.url = data.xpath('//span[contains(., "Strona producenta")]/following-sibling::*[1]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title'].replace(u'\uFEFF', '').strip()
    review.url = context['url']
    review.ssid = product.ssid

    author = data.xpath('//span[@class="author"]/text()').string()
    if author:
        author = author.replace('Autor: ', '').strip()
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//span[contains(text(), "Plusy")]/following-sibling::*[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.replace(u'\uFEFF', '').strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[contains(text(), "Minusy")]/following-sibling::*[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.replace(u'\uFEFF', '').strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="article_header" and not(.//span[contains(@class, "title")])]//text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('(//div[@class="article_body_ramka_in"]|//div[@class="article_body_ramka_in"]/span[@class="bold"])/text()[not(preceding::span[@class="bold" and regexp:test(., "Cena:|Strona producenta")] or regexp:test(., "Cena:|Strona producenta|Plusy|Minusy|Zobacz także:"))]').string(multiple=True)

    pages = data.xpath('(//td[span[@class="padPages"]])[1]/span')
    for page in pages:
        page_url = page.xpath('a/@href').string().split('#')[0] if page.xpath('a/@href') else data.response_url
        page_num = page.xpath('.//text()').string(multiple=True)
        title = review.title + ' - Pagina ' + str(page_num)
        review.add_property("pages", value=dict(title=title, url=page_url))

    if pages:
        session.do(Request(page_url, use='curl', force_charset='utf-8', max_age=0), process_review_lastpage, dict(excerpt=excerpt, review=review, product=product))

    elif excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_lastpage(data: Response, context: dict[str, str], session: Session):
    review = context['review']

    pros = data.xpath('//span[contains(text(), "Plusy")]/following-sibling::*[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.replace(u'\uFEFF', '').strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[contains(text(), "Minusy")]/following-sibling::*[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.replace(u'\uFEFF', '').strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    excerpt = data.xpath('(//div[@class="article_body_ramka_in"]|//div[@class="article_body_ramka_in"]/span[@class="bold"])/text()[not(preceding::span[@class="bold" and regexp:test(., "Cena:|Strona producenta")] or regexp:test(., "Cena:|Strona producenta|Plusy|Minusy|Zobacz także:"))]').string(multiple=True)
    if excerpt:
        context['excerpt'] += ' ' + excerpt

    if context['excerpt']:
        excerpt = context['excerpt'].replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)

        session.emit(product)