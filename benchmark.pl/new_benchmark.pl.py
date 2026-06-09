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
    session.queue(Request('https://www.benchmark.pl/testy-7257465008464449k', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//a[.//h2[@data-title="true"]]')
    for rev in revs:
        id = rev.xpath('@id').string()
        title = rev.xpath('.//h2[@data-title="true"]/text()').string()
        url = rev.xpath('@href').string().split('?')[0]
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url, id=id))

    next_url = data.xpath('//a[@data-pagination="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' - recenzja')[0].replace('Przetestowałem ', '').replace('Recenzja ', '').replace('Test procesora ', '').replace(' - test', '').replace('Test ', '').strip()
    product.url = context['url']
    product.ssid = context['id']

    product.category = data.xpath('(//a[@class="breadcrumbs-item-link" and not(contains(., "Testy") or contains(., "Benchmark"))])[last()]//text()').string()
    if not product.category:
        product.category = 'Technologia'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('(//a[contains(@class, "article-author-link")]|//div[contains(@class, "article-author")]/span)/text()').string()
    author_url = data.xpath('//a[contains(@class, "article-author-link")]/@href').string()
    if author and author_url:
        author_url = author_url.split('?')[0]
        author_ssid = author_url.split('-')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//div[contains(h2, "Plusy")]/following-sibling::*[1]/ul/li')
    if not pros:
        pros = data.xpath('//div[contains(h2, "Warto kupić, jeśli")]/following-sibling::*[1]/ul/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(h2, "Minusy")]/following-sibling::*[1]/ul/li')
    if not cons:
        cons = data.xpath('//div[contains(h2, "Nie warto, jeśli")]/following-sibling::*[1]/ul/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "article-lead")]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//div[contains(h2, "Dla kogo jest ten aparat") or contains(h2, "Czy warto kupić")])[last()]/following-sibling::div/p[not(contains(., "Produkt do przeprowadzenia testu"))][preceding::h2[1][contains(., "Dla kogo jest ten aparat") or contains(., "Czy warto kupić")]]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(h2, "Dla kogo jest ten aparat") or contains(h2, "Czy warto kupić")]/preceding-sibling::div/p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content-text")]/p[not(contains(., "Produkt do przeprowadzenia testu"))][not(preceding::h2[1][contains(., "Dla kogo jest ten aparat") or contains(., "Czy warto kupić")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
