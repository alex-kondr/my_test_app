from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request('https://www.parfym.se/', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="menu__levelc__submenu"]')
    for cat in cats:
        name = cat.xpath('.//a[@class="title"]/text()').string()

        if 'märken' not in name.lower() and 'nyheter' not in name.lower() and 'aktuella' not in name.lower() and 'populära' not in name.lower():
            sub_cats = cat.xpath('.//a[@class="pfour-menu-medium"]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string()

                if 'märken' not in sub_name:
                    session.queue(Request(url + '?layout=pfour_products'), process_prodlist, dict(cat=name + '|' + sub_name, prods_url=url))
            else:
                url = cat.xpath('.//a[@class="title"]/@href').string()
                session.queue(Request(url + '?layout=pfour_products'), process_prodlist, dict(cat=name, prods_url=url))


def process_prodlist(data, context, session):
    try:
        prods_json = simplejson.loads(data.content)
    except:
        return

    new_data = data.parse_fragment(prods_json.get('products'))

    prods = new_data.xpath('//div[@class="pfour-prod-item pfour-hasplusbutton"]')
    for prod in prods:
        name = prod.xpath('.//div[@class="name"]/text()').string()
        manufacturer = prod.xpath('.//div[@class="brand"]/text()').string()
        prod_id = prod.xpath('.//button/@data-productid').string()
        url = prod.xpath('.//a[@class="pfour-prod-item-link"]/@href').string()

        revs_cnt = prod.xpath('.//div[@class="reviews"]/span[@class="no"]/text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, manufacturer=manufacturer, prod_id=prod_id, url=url))

    next_page = context.get('page', 1) + 1
    offset = context.get('offset', 0) + 24
    if prods:
        next_url = context['prods_url'] + '?layout=pfour_products&page=' + str(next_page) + '&skip=' + str(offset)
        session.queue(Request(next_url), process_prodlist, dict(context, page=next_page, offset=offset))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['prod_id']
    product.sku = product.ssid
    product.manufacturer = context['manufacturer']
    product.category = context['cat']

    prod_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        sku = prod_json.get('sku')
        if sku:
            product.sku = sku.split('-')[0]

    ean = data.xpath('//div[text()="EAN"]/following-sibling::div/text()').string()
    if ean:
        ean = ean.split(',')[0]
        if ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)


    revs = data.xpath('//div[@class="pfour-product-detail-reviewmenu__body__review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        review.date = rev.xpath('.//div[contains(@class, "date")]/text()').string()

        author = rev.xpath('.//div[contains(@class, "stars__name")]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//img[@alt="Star"])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        excerpt = rev.xpath('.//div[contains(@class, "text")]//text()').string(multiple=True)
        if excerpt:
            excerpt = excerpt.strip(' •+-')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
