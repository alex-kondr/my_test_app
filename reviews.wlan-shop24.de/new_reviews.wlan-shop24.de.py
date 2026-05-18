from agent import *
from models.products import *
import simplejson


XCAT = ['Service', 'SALE!']


def run(context, session):
    session.queue(Request('https://www.wlan-shop24.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@id="cat-ul"]/li')
    for cat in cats:
        name = cat.xpath('a/text()').string(multiple=True)

        if name and name not in XCAT:
            cats1 = cat.xpath('ul/li/div/div/div[a]')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a/span[contains(@class, "title")]/text()').string()

                if cat1_name not in XCAT:
                    subcats = cat1.xpath('ul/li/a')
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.xpath('text()').string()
                            url = subcat.xpath('@href').string()
                            session.queue(Request(url+'?Sortierung=12'), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                    else:
                        url = cat1.xpath('a/@href').string()
                        session.queue(Request(url+'?Sortierung=12'), process_prodlist, dict(cat=name+'|'+cat1_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(a/@class, "title")]')
    for prod in prods:
        name = prod.xpath('a[contains(@class, "title")]/text()').string()
        url = prod.xpath('a[contains(@class, "title")]/@href').string()

        rating = prod.xpath('div[@aria-label="Bewertungen"]')
        if rating:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))
        else:
            return

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.sku = data.xpath('//li[contains(strong/text(), "Artikelnummer:")]/span/text()').string()
    product.category = context['cat']

    product.ssid = data.xpath('//input/@data-product-id').string()
    if not product.ssid:
        product.ssid = product.sku

    manufacturer = data.xpath('//div[contains(strong/text(), "Herstellerinformationen:")]/text()[contains(., "Name:")]').string()
    if manufacturer:
        product.manufacturer = manufacturer.replace('Name:', '').strip()

    mpn = data.xpath('//li[contains(strong/text(), "HAN:")]/span/text()').string()
    if mpn and len(mpn) > 5:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//li[contains(strong/text(), "GTIN:")]/span/text()').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs_url = product.url + '?ratings_nPage=0&btgsterne=0'
    session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[contains(@class, "review-comment")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//blockquote/small/text()').string(multiple=True)
        if date:
            review.date = date.replace('| Verifizierter Kauf', '').split('|')[-1].strip()

        author = rev.xpath('.//blockquote/small/text()').string(multiple=True)
        if author:
            author = author.split('|')[0].strip()
            if len(author) > 1 and 'anonym' not in author.lower():
                review.authors.append(Person(name=author, ssid=author))
            else:
                author = None

        grade_overall = rev.xpath('.//small[contains(., " von")]/span[1]/text()').string()
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//blockquote/small[contains(text(), "Verifizierter Kauf")]')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.xpath('.//div[contains(@class, "title")]/strong/text()').string(multiple=True)
        excerpt = rev.xpath('.//blockquote/p//text()').string(multiple=True)
        if excerpt and len(excerpt) > 2:
            review.title = title
        else:
            excerpt = title

        if excerpt and len(excerpt) > 2:
            review.add_property(type="excerpt", value=excerpt)

            ssid = rev.xpath('@id').string()
            if ssid:
                review.ssid = ssid.replace('comment', '')
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    next_url = data.xpath('//ul[contains(@class, "pagination")]/li/a[contains(., "»")]/@href').string()
    if next_url:
        session.do(Request(next_url), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
