from agent import *
from models.products import *


XCAT = ['Sale', 'Education', 'Community', 'Free expert advice']


def process_frontpage(data, context, session):
    cats = data.xpath("//a[@class='level-top']")
    for cat in cats:
        name = cat.xpath('.//text()').string()
        url = cat.xpath("@href").string()
        if name not in XCAT:
             session.queue(Request(url), process_productlist, dict(category=name))


def process_productlist(data, context, session):
    prods = data.xpath("//ol[@class='products list items product-items']/li[@class='item product product-item']")
    for prod in prods:
        name = prod.xpath(".//a[@class='product-item-link']//text()").string()
        url = prod.xpath(".//a[@class='product-item-link']/@href").string()
        rating = prod.xpath(".//div[@class='rating-result']")
        if rating:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_page = data.xpath("//a[@class='action next']/@href").string()
    if next_page:
        session.queue(Request(next_page), process_productlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['category']
    product.manufacturer = data.xpath('//div[@data-th="Brands"]//text()').string()
    product.description = data.xpath('//div[@class="short-article"]//text()').string(multiple=True)
    product.sku = data.xpath("//div[@class='product attribute sku']//div[@class='value']//text()").string()

    subcat = data.xpath("//span[@class='categories']//span[@class='category'][last()]//text()").string()
    if subcat:
        subcat = subcat.split("/")[-1]
        product.category = product.category + '|' + subcat

    ssid = data.xpath('//span[@class="product_id"]//text()').string()
    product.ssid = product.sku or ssid

    ean = data.xpath("//div[@data-th='EAN']//text()").string()
    if ean:
        product.add_property(type="id.ean", value=ean)

    url = 'https://www.camerapro.com.au/review/product/listAjax/id/' + ssid
    session.do(Request(url), process_reviews, dict(context, product=product))


def process_reviews(data, context, session):
    product = context['product']

    for rev in data.xpath('//div[@class="review-description"]'):
        review = Review()
        review.type = 'user'
        review.url = context['url']
        review.title = rev.xpath("preceding-sibling::node()/text()").string()
        review.date = rev.xpath('ancestor::div[@class="review-content"]/preceding-sibling::p//text()').string(multiple=True)

        excerpt = rev.xpath(".//text()").string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

        author = rev.xpath('ancestor::body[1]/preceding-sibling::body[1]//p[@class="review-details-author"]//text()').string(multiple=True)
        review.authors.append(Person(name=author, ssid=author))

        grade = rev.xpath('ancestor::div[@class="review-content"]/preceding-sibling::span//text()').string(multiple=True)
        if grade:
            grade = float(grade.replace('%', '')) / 20
            review.grades.append(Grade(type="overall", value=grade, best=5.0))

        review.ssid = '%s-%s' % (product.ssid, hashlib.md5(author + excerpt).hexdigest())
        product.reviews.append(review)

    if product.reviews:
        session.emit(product)


def run(context, session):
    session.queue(Request('https://www.camerapro.com.au/'), process_frontpage, dict())
