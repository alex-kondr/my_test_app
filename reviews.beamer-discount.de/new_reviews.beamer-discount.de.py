from agent import *
from models.products import *
import time


SLEEP = 2
OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""
XCAT = ['Nach Hersteller', 'alle anzeigen', 'Nach Größen', 'Sale', 'BLOG']


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
    session.queue(Request('https://www.beamer-discount.de/', use='curl', options=OPTIONS), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    time.sleep(SLEEP)

    cats = data.xpath('//div[@class="advanced-menu"]/div')
    for cat in cats:
        name = cat.xpath('div/a/@title').string().replace('Zur Kategorie', '').replace('Weiteres', '').strip()
        url = cat.xpath('div/a/@href').string()

        if name not in XCAT:
            cats1 = cat.xpath('div/ul/li')

            for cat1 in cats1:
                cat1_name = cat1.xpath('a/text()').string()

                if cat1_name not in XCAT:
                    if 'Alle' in cat1_name:
                        cat1_name = ''

                    subcats = cat1.xpath('ul/li/a')
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.xpath('.//text()').string()
                            url = subcat.xpath('@href').string()

                            if subcat_name not in XCAT:
                                session.queue(Request(url+'?n=74', use='curl', options=OPTIONS), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))

                    else:
                        url = cat1.xpath('a/@href').string()
                        session.queue(Request(url+'?n=74', use='curl', options=OPTIONS), process_prodlist, dict(cat=name+'|'+cat1_name))

def process_prodlist(data, context, session):
    strip_namespace(data)

    time.sleep(SLEEP)

    prods = data.xpath('//div[@class="product--info"][.//span[@class="product--rating"]]/a[@class="product--title"]')
    for prod in prods:
        name = prod.xpath('@title').string()
        url = prod.xpath('@href').string().split('?')[0]
        session.queue(Request(url, use='curl', options=OPTIONS), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url+'&n=74', use='curl', options=OPTIONS), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    time.sleep(SLEEP)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//meta[@itemprop="productID"]/@content').string()
    product.sku = data.xpath('//span[@itemprop="sku"]/text()').string()
    product.category = context['cat'].replace('Sonstiges Zubehör', '').replace('||', '|').strip(' |')
    product.manufacturer = data.xpath('//meta[@property="product:brand"]/@content').string()

    ean = data.xpath('//meta[contains(@itemprop, "gtin")]/@content').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//meta[@itemprop="datePublished"]/@content').string()

        author = rev.xpath('.//span[@itemprop="author"]//text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//meta[@itemprop="ratingValue"]/@content').string()
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0, worst=0.5))

        title = rev.xpath('.//h4[@class="content--title"]/text()').string()
        excerpt = rev.xpath('.//p[@itemprop="reviewBody"]/text()').string(multiple=True)
        if excerpt:
            review.title = title
        elif title:
            excerpt = title

        if excerpt and len(excerpt) > 2:
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # All revs loaded
