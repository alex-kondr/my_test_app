from agent import *
from models.products import *


X_CATS = ['FINANCE', 'SPECIAL OFFERS', 'EX-DISPLAY / PRE-LOVED', 'FIND BY PART', ]
NO_SUBCATS = ['Sewing Machines', 'Overlockers', 'Ironing Presses']


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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request("https://coulingsewingmachines.co.uk/"), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class="navPages-list"]/li')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        if name not in X_CATS:
            cats1 = cat.xpath('(.//ul[@class="navPage-subMenu-list"]/li)[position() > 1]')

            if cats1 and name not in NO_SUBCATS:
                for cat1 in cats1:
                    cat1_name = cat1.xpath('a//text()').string(multiple=True)

                    if cat1_name not in X_CATS:
                        subcats = cat1.xpath('ul[@class="navPage-childList"]/li/a')
                        if subcats:
                            for subcat in subcats:
                                subcat_name = subcat.xpath('.//text()').string(multiple=True)
                                url = subcat.xpath('@href').string()
                                session.queue(Request(url), process_prodlist, dict(cat=name + "|" + cat1_name + "|" + subcat_name))
                        else:
                            url = cat1.xpath('a/@href').string()
                            session.queue(Request(url), process_prodlist, dict(cat=name + "|" + cat1_name))
            else:
                url = cat.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//li[@class="product"]')
    for prod in prods:
        name = prod.xpath('.//h4[@class="listItem-title"]/a//text()').string()
        url = prod.xpath('.//h4[@class="listItem-title"]/a/@href').string()
        ssid = prod.xpath('.//button/@data-product-id').string()
        brand = prod.xpath('article/@data-product-brand').string() or prod.xpath('.//p[@class="listItem-brand"]//text()').string()

        rating = prod.xpath('.//span[contains(@class, "ratingFull")]')
        if rating:
            session.queue(Request(url), process_product, dict(context, name=name, url=url, ssid=ssid, brand=brand))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.manufacturer = context['brand']
    product.ssid = context['ssid']

    mpn = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    if mpn and mpn.lower() in product.url:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//dd[@data-product-upc="data-product-upc"]//text()').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    # revs_cnt = data.xpath('//a[@id="productReview_link"]//text()').string()
    # if revs_cnt:
    #     revs_cnt = revs_cnt.split(' review')[0].lstrip('(')

    revs = data.xpath('//li[@class="productReview"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//p[@class="productReview-author"]//text()').string()
        if date:
            review.date = date.split(' on ')[-1]

        author = rev.xpath('.//meta[@itemprop="author"]/@content').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@itemprop="ratingValue"]//text()').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.xpath('.//h5[@class="productReview-title"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[@class="productReview-body"]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.strip(' +-*.:;•,–')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # No next page, no more than 10 revs
