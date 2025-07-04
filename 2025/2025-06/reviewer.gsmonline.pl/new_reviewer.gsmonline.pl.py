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
    session.queue(Request('https://gsmonline.pl/testy', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//a[contains(@id, "article_big")]')
    for rev in revs:
        ssid = rev.xpath('@id').string().split('_')[-1]
        title = rev.xpath('.//h3/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, ssid=ssid, url=url))

    next_url = data.xpath('//a[@class="last"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('Test - ', '').split(' - ')[0].split(' – ')[0].split(': test')[0].replace('Rozpoczynamy testy ', '').replace('Zaczynamy testy ', '').replace('Nasz test ', '').replace('Testujemy ', '').replace('Przetestowaliśmy ', '').replace('Recenzja ', '').replace('Test ', '').strip().capitalize()
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = 'Technologia'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//div[@class="article-date"]/text()').string()

    author = data.xpath('//a[@class="author_email"]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//h3[contains(., "Zalety:")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' +-*.')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//h3[contains(., "Wady:")]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(' +-*.')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h3[contains(., "Podsumowanie")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h3[contains(., "Podsumowanie")])[1]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="article-full"]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
