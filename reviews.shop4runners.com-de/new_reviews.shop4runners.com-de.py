from agent import *
from models.products import *


DUPE_PRODS = []
XCAT = ['Sale', 'NEUHEITEN', 'Bestseller', 'Neuheiten', 'BESTSELLER']


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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://shop4runners.com', force_charset='utf-8', use='curl'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//div[@x-ref="nav-mobile"]//div[contains(@class, "navigation--level-top")]')
    for cat in cats:
        name = cat.xpath('a/div/text()').string()

        cats1 = cat.xpath('template/div[contains(@class, "nav__level-1")]/div[contains(@class, "category-item")]')
        for cat1 in cats1:
            cat1_name = cat1.xpath('div[contains(@class, "nav-item--and-text")]/div/a[contains(@class, "title")]/text()').string()

            if cat1_name not in XCAT:
                subcats = cat1.xpath('.//div[contains(@class, "nav__column")]/div[contains(@class, "navigation__container")]/div[contains(@class, "nav__column")]/div')
                for subcat in subcats:
                    subcat_name = subcat.xpath('div[contains(@class, "nav-item--category")]/a/text() | div[contains(@class, "nav-item--and-text")]/div/a[contains(@class, "title")]/text()').string()
                    if 'weitere' in subcat_name.lower():
                        subcat_name = ''

                    if subcat_name not in XCAT:
                        url = subcat.xpath('div[contains(@class, "nav-item--category")]/a/@href | div[contains(@class, "nav-item--and-text")]/div/a[contains(@class, "title")]/@href').string()
                        session.queue(Request(url, force_charset='utf-8', use='curl'), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "product-info")]')
    for prod in prods:
        name = prod.xpath('.//a[contains(@class, "product-item-link")]/span/text()').string(multiple=True)
        url = prod.xpath('.//a[contains(@class, "product-item-link")]/@href').string()

        rating = prod.xpath('.//div[contains(@class, "rating-number")]/span/text()').string()
        if rating and float(rating) > 0:
            session.queue(Request(url, force_charset='utf-8', use='curl'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8', use='curl'), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    if context['url'] in DUPE_PRODS:
        return

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//form[@id]/input[@name="product"]/@value').string()
    product.sku = data.xpath('//meta[@itemprop="sku"]/@content').string()
    product.category = context['cat'].replace('||', '|').strip('|')
    product.manufacturer = data.xpath('//div[@itemprop="brand"]/meta/@content').string()

    mpn = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//section/@data-loadbee-gtin').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[contains(@id, "reviews-list")]/div//div[contains(@class, "reviews-list__review")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//time/@datetime').string()

        author = rev.xpath('.//div[contains(@class, "items-center") and contains(div/@class, "rating")]/strong[@itemprop="author"]/span/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//div[@class="rating-summary__star"])')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.xpath('div[contains(@class, "font-bold")]/text()').string()
        excerpt = rev.xpath('div[contains(@class, "text-base-v3")]//text()').string(multiple=True)
        if excerpt and len(excerpt.strip(' ,+*')) > 2:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.strip(' ,+*')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

        prod_variants = data.xpath('//div[contains(@class, "grouped-product")]/a/@href').strings()
        if prod_variants and len(prod_variants) > 0:
            DUPE_PRODS.extend(prod_variants)

    # Loaded all revs
