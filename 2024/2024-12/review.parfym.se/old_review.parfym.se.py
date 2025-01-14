from agent import *
from models.products import *
import simplejson


XCAT = ["Märken", "Gåvor vid köp!", 'Varumärken', 'Nyheter', 'Män', 'Presentkort', 'Jul', 'Populära parfymmärken', 'Professionell hårvård', 'Populära hudvårdsmärken', 'Professionella hudvårdsmärken', 'Premium sminkmärken', 'Populära sminkmärken', 'Populära doftfamiljer', 'Hårprodukter för män', 'Hudvård för män']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request("https://www.parfym.se/", force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    cats1 = data.xpath('//li[@class="mobile-menu-main-list-item"]')
    for cat1 in cats1:
        name1 = cat1.xpath("a/text()").string()

        if name1 not in XCAT:
            cats2 = cat1.xpath('ul/li')
            for cat2 in cats2:
                name2 = cat2.xpath('a[not(contains(., "Visa alla"))]/text()').string()

                if name2 not in XCAT:
                    if name2 == name1:
                        name2 = ''

                    cats3 = cat2.xpath('ul/li/a[not(contains(., "Visa alla"))]')
                    if not cats3:
                        url = cat2.xpath('a[not(contains(., "Visa alla"))]/@href').string()
                        if url:
                            session.queue(Request(url + '?page=10000', force_charset='utf-8'), process_prodlist, dict(cat=name1 + '|' + name2))

                    for cat3 in cats3:
                        name3 = cat3.xpath('text()').string()
                        if name3 == name2:
                            name3 = ''

                        url = cat3.xpath('@href').string()
                        if url:
                            session.queue(Request(url+'?page=10000', force_charset='utf-8'), process_prodlist, dict(cat=name1+'|'+name2+'|'+name3))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@data-gtmimpressionjs]')
    for prod in prods:
        name = prod.xpath('.//div[@class="name"]/text()').string()
        url = prod.xpath('a[@class="prod-item-link"]/@href').string()
        revs_cnt = prod.xpath('.//span[@class="no"]/text()').string()
        if revs_cnt:
            revs_cnt = int(revs_cnt.strip(' ()'))
            if name and url and revs_cnt > 0:
                session.queue(Request(url, force_charset='utf-8'), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.category = context["cat"].replace('||', '|').strip(' |')
    product.manufacturer = data.xpath('//span[@class="brand-name"]/text()').string()
    product.ssid = product.url.split('/')[-1]
    product.sku = data.xpath('//input[@name="productId"]/@value').string()

    ean = data.xpath('//dt[regexp:test(., "ean:", "i")]/following-sibling::dd/text()').string()
    if ean:
        ean = ean.split(',')[0]
        product.properties.append(ProductProperty(type='id.ean', value=ean))

    revs = data.xpath('//div[@class="desktop-brand"]//div[@class="review"]')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.date = rev.xpath('.//div[@class="date"]/text()').string()

        author_name = rev.xpath('.//div[@class="name"]/text()').string()
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = rev.xpath('div[@class="stars"]/img')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(len(grade_overall)), best=5.0))

        excerpt = rev.xpath('div[@class="text"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest() if author_name else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
