from agent import *
from models.products import *
import simplejson


XCAT = ["Used Products", "Specials", "Services", "Gifts"]


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

                sub_cats1 = sub_cat.xpath('ul[contains(@class, "submenu")]/li')
                if sub_cats1:
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('a//text()').string(multiple=True)

                        sub_cats2 = sub_cat1.xpath('ul[contains(@class, "submenu")]/li')
                        if sub_cats2:
                            for sub_cat2 in sub_cats2:
                                sub_name2 = sub_cat2.xpath("a//text()").string(multiple=True)
                                url = sub_cat2.xpath('a/@href').string()
                                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1 + '|' + sub_name2))
                        else:
                            url = sub_cat1.xpath('a/@href').string()
                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                else:
                    url = sub_cat.xpath('a/@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath("//strong[@class='product name product-item-name']/a[@class='product-item-link']")
    for prod in prods:
        name = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_page = data.xpath("//link[@rel='next']//@href").string()
    if next_page:
        session.queue(Request(next_page), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath("//div[@class='product attribute sku']/div[@itemprop='sku']//text()").string()
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = context['name'].split(" ")[0]

    mpn = data.xpath("//div[@class='product-info-main']/div[@class='product-data']/div/span[contains(., 'MPN')]/following-sibling::div//text()").string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath("//div[@class='product-info-main']/div[@class='product-data']/div/span[contains(., 'UPC')]/following-sibling::div//text()").string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    url = 'https://www.shopperapproved.com/product/15521/' + str(product.ssid) + '.js'
    session.do(Request(url, use='curl'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    if 'tempreviews' not in data.content:  # Product has no reviews
        return

    revs_json = data.content.replace("\n", "").split("var tempreviews = ")[-1].split(";sa_product_reviews")[0].split(";sa_merchant_reviews")[0]
    revs = simplejson.loads(revs_json)
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.title = rev['heading']
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