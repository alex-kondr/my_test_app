from agent import  *
from models.products import *


XCAT = ['Second Hand', 'AREA', 'Aktionen %', 'Workshops', 'Blog', 'Geschenkgutscheine', 'alle', 'Angebote']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.fotokoch.de/index.html'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[contains(@class, "checkboxhack_nav_more item_") and div[contains(@class, "checkboxhack_nav_more")]]')
    for cat in cats:
        name = cat.xpath('span[@class="nav_backward"]/span/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('div[contains(@class, "checkboxhack_nav_more")]')
            for cat1 in cats1:
                cat1_name = cat1.xpath('span[@class="nav_backward"]/span/text()').string()
                url = cat1.xpath('a[@class="nav_desktop_level_2 navi"]/@href').string()

                if cat1_name and cat1_name not in XCAT:
                    cat1_name = cat1_name.replace('Weitere ', '').title()
                    session.queue(Request(url), process_catlist, dict(cat=name + '|' + cat1_name))


def process_catlist(data, context, session):
    subcats = data.xpath('//div[@id="level_seitenmenu"]/a')
    for subcat in subcats:
        subcat_name = subcat.xpath('text()').string().replace('von ', '').replace('für ', '').strip()
        url = subcat.xpath('@href').string()

        if subcat_name not in XCAT:
            session.queue(Request(url + '?listenlimit=0,50'), process_prodlist, dict(cat=context['cat'] + '|' + subcat_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="flex-masonry"]')
    for prod in prods:
        name = prod.xpath('.//div[@class="_b"]//a/@title').string()
        url = prod.xpath('.//div[@class="_b"]//a/@href').string()

        revs_cnt = prod.xpath('.//div[@class="_c"]//text()[regexp:test(., "^\(\d+\)$")]').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat'].replace('nach Marke|', '|').replace('Nach Marke|', '|').replace('||', '|')
    product.manufacturer = data.xpath('//head[meta[@itemprop="sku"]]/meta[@itemprop="name"]/@content').string()

    ssid = data.xpath('//meta[@itemprop="sku"]/@content').string()
    if not ssid:
        ssid = product.url.split('_')[-1].replace('.html', '')

    product.ssid = ssid
    product.sku = product.ssid

    mpn = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//div[contains(., "EAN")]/following-sibling::div[@class="_td last"]//span/text()').string()
    if ean and ean.isdigit() and len(ean) > 11:
        product.add_property(type='id.ean', value=ean)

    session.queue(Request(product.url.replace('.html', '_bewertungen.html')), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="flex-container bewertung-liste"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//div[@class="bewertung-user"]//span[contains(., "am")]/text()[normalize-space()]').string()
        if date:
            review.date = date.replace('am ', '').split()[0]

        author = rev.xpath('.//div[@class="bewertung-user"]//span[contains(., "von")]/text()[normalize-space()]').string()
        if author:
            author = author.replace('von ', '')
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@class="sterne active"]/@title').string()
        if grade_overall:
            grade_overall = float(grade_overall.split()[0])
            if grade_overall > 0:
                review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        is_recommended = rev.xpath('.//p[contains(., "Ich kann dieses Produkt weiterempfehlen!")]//text()[normalize-space()]').string()
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        title = rev.xpath('.//h4[normalize-space()]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[@class="bewertung-text"]//text()[normalize-space()]').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
