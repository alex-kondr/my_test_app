from agent import *
from models.products import *
import simplejson


XCAT = ["Used Products", "Specials", "Services", "Gifts", "Audio Cables", "Cables & PC Sync", "Power Supplies & Cables"]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.districtcamera.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@id="store.menu"]/ul/li[contains(@class, "megamenu")]')
    for cat in cats:
        name = cat.xpath("a//text()").string(multiple=True)

        sub_cats = cat.xpath('ul[contains(@class, "submenu")]/li[contains(@class, "megamenu")]')
        if name not in XCAT:
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a//text()').string(multiple=True)

                if sub_name not in XCAT:
                    sub_cats1 = sub_cat.xpath('ul[contains(@class, "submenu")]/li')
                    if sub_cats1:
                        for sub_cat1 in sub_cats1:
                            sub_name1 = sub_cat1.xpath('a//text()').string(multiple=True)

                            if sub_name1 not in XCAT:
                                sub_cats2 = sub_cat1.xpath('ul[contains(@class, "submenu")]/li')
                                if sub_cats2:
                                    for sub_cat2 in sub_cats2:
                                        sub_name2 = sub_cat2.xpath("a//text()").string(multiple=True)

                                        if sub_name2 not in XCAT:
                                            url = sub_cat2.xpath('a/@href').string()
                                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1 + '|' + sub_name2))
                                else:
                                    url = sub_cat1.xpath('a/@href').string()
                                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                    else:
                        url = sub_cat.xpath('a/@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product details product-item-details"]')
    for prod in prods:
        name = prod.xpath('.//a[@class="product-item-link"]/text()').string()
        ssid = prod.xpath('div/@data-product-id').string()
        url = prod.xpath('.//a[@class="product-item-link"]/@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, ssid=ssid, url=url))

    next_page = data.xpath("//link[@rel='next']//@href").string()
    if next_page:
        session.queue(Request(next_page), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[@class="amshopby-option-link"]/a/@title').string()

    mpn = data.xpath("//div[@class='product-info-main']/div[@class='product-data']/div/span[contains(., 'MPN')]/following-sibling::div//text()").string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath("//div[@class='product-info-main']/div[@class='product-data']/div/span[contains(., 'UPC')]/following-sibling::div//text()").string()
    if ean and ean.isdigit() and len(ean) > 11:
        product.add_property(type='id.ean', value=ean)

    pid = data.xpath("//div[@class='product attribute sku']/div[@itemprop='sku']//text()").string()
    url = 'https://www.shopperapproved.com/product/15521/' + str(pid) + '.js'
    session.do(Request(url, use='curl'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    try:
        revs_json = data.content.replace("\n", "").split("var tempreviews = ")[-1].split(";sa_product_reviews")[0].split(";sa_merchant_reviews")[0]
        revs = simplejson.loads(revs_json)
    except:
        return

    for rev in revs:
        review = Review()
        review.type = 'user'
        review.title = rev.get('heading')
        review.url = product.url
        review.ssid = rev['id']
        review.date = rev.get('date')

        author = rev.get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade = rev.get('rating')
        if grade:
            review.grades.append(Grade(type='overall', value=float(grade), best=5.0))

        recommend = rev.get('recommend')
        if recommend:
            review.add_property(type='is_recommended', value=True)

        verified_buyer = rev.get('verified')
        if verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.get('comments')
        if excerpt and len(excerpt) > 3:
            excerpt = excerpt.replace('<br>', '').replace('&#039;', "'")
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
