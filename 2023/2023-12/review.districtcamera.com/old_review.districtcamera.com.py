from agent import *
from models.products import *
import simplejson


XCAT = ["Used Products", "Closeouts / Specials", "Rentals"]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.districtcamera.com/', use='curl'), process_frontpage, dict())


def process_frontpage(data, context, session):
    for cat in data.xpath("//nav[@class='navigation']/following-sibling::ul/li/a[@class='level-top']"):
        name = cat.xpath(".//text()").string()
        url = cat.xpath("@href").string()
        if name not in XCAT:
            session.queue(Request(url, use='curl'), process_subcategory, dict(cat=name))


def process_subcategory(data, context, session):
    cats = data.xpath("//ul[@class='cat-thumbs row']/li/h3[@class='subcat-title']/a")
    for cat in cats:
        name = cat.xpath("text()").string(multiple=True)
        url = cat.xpath("@href").string()
        session.queue(Request(url, use='curl'), process_subcategory, dict(cat=context['cat']+"|"+name))

    if not cats:
        process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    prods = data.xpath("//strong[@class='product name product-item-name']/a[@class='product-item-link']")
    for prod in prods:
        name = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url, use='curl'), process_product, dict(context, name=name, url=url))

    next_page = data.xpath("//link[@rel='next']//@href").string()
    if next_page:
        session.queue(Request(next_page, use='curl'), process_prodlist, context)


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
    if not 'tempreviews' in data.content:  # Product has no reviews
        return

    revs = simplejson.loads(data.content.replace("\n", "").split("var tempreviews")[-1].split("=", 1)[-1].split(";sa_product_reviews")[0])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.title = rev['heading']
        review.url = product.url
        review.ssid = rev['id']
        review.date = rev['date']
        review.authors.append(Person(name=rev['name'], ssid=rev['name']))
        review.grades.append(Grade(type='overall', name='Overall score', value=rev['rating'], best=5.0))

        verified_buyer = rev['verified']
        if verified_buyer == True:
            review.add_property(type='is_verified_buyer', value=True)

        if rev['comments']:
            review.properties.append(ReviewProperty(type='excerpt', value=rev['comments']))

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
