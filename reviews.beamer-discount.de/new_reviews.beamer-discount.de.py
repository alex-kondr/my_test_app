from agent import *
from models.products import *
import time
import random


XCAT = ['Marken', 'Angebote & B-Ware|Aktuelle Deals', 'Ratgeber']


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
    session.queue(Request('https://www.beamer-discount.de/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    cats = data.xpath('//nav[@aria-label="Primär"]/ul/li')
    for cat in cats:
        name = cat.xpath('div[contains(@class, "row")]/a/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('div/div/ul/li')
            for cat1 in cats1:
                cat1_name = cat1.xpath('div[contains(@class, "item")]/a/text()').string()

                if cat1_name not in XCAT:
                    subcats = cat1.xpath('div/ul/li/a')
                    for subcat in subcats:
                        subcat_name = subcat.xpath('.//text()').string(multiple=True)
                        url = subcat.xpath('@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    prods = data.xpath('//product-card')
    for prod in prods:
        name = prod.xpath('.//span[contains(@class, "card-title-main")]/text()').string()
        ssid = prod.xpath('@data-product-id').string()
        url = prod.xpath('.//a[contains(@class, "prod-link")]/@href').string().split('?')[0]

        revs_cnt = prod.xpath('.//div[contains(@class, "rating__count")]/text()').string()
        if revs_cnt and int(revs_cnt.strip('( )')) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, ssid=ssid, url=url, revs_cnt=revs_cnt))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = data.xpath('//span[@class="product-sku__value"]/text()').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//li[contains(div/text(), "Marke")]/div[contains(@class, "value")]//text()').string()

    mpn = data.xpath('//li[contains(div/text(), "Hersteller-Artikelnumme")]/div[contains(@class, "value")]//text()').string(multiple=True)
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//li[contains(div/text(), "EAN")]/div[contains(@class, "value")]//text()').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[@data-review-id]')
    revs.pretty()

    if len(revs) != int(context['revs_cnt'].strip('( )')):
        raise ValueError("!!!")

    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@data-review-id').string()

        date = rev.xpath('.//time/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//span[contains(@class, "rev__author")]/text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[contains(@class, "rating")]/@data-score').string()
        if grade_overall and grade_overall.isdigit() and float(grade_overall) > 0:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.xpath('@data-verified-buyer').string()
        if is_verified_buyer and is_verified_buyer == 'true':
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.xpath('@data-thumb-up-count').string()
        if hlp_yes and hlp_yes.isdigit() and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('@data-thumb-down-count').string()
        if hlp_no and hlp_no.isdigit() and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.xpath('.//strong[contains(@class, "title")]/text()').string()
        excerpt = rev.xpath('.//div[contains(@class, "rev__bod")]/p//text()').string(multiple=True)
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