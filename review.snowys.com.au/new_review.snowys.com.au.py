from agent import *
from models.products import *
import simplejson


X_CATS = ['Clearance']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=9000)]
    session.queue(Request("https://www.snowys.com.au/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="mega-menu-list-root"]')
    for cat in cats:
        name = cat.xpath('a//text()').string()
        url = cat.xpath('a/@href').string()

        subcats = cat.xpath('div[@class="mega-menu-list-box"]/ul[1]/li/a')
        if subcats:
            for subcat in subcats:
                subcat_name = subcat.xpath('text()').string()
                url = subcat.xpath('@href').string()
                if subcat_name not in X_CATS:
                    session.queue(Request(url), process_prodlist, dict(cat=name + "|" + subcat_name))
        elif name not in X_CATS:
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-item"]')
    for prod in prods:
        name = prod.xpath('.//span[@class="productName"]//text()').string()
        url = prod.xpath('.//a[@class="product-linksubarea"]/@href').string()
        ssid = prod.xpath('@data-productid').string()
        brand = prod.xpath('.//span[@class="brandName"]//text()').string()

        revs_count = prod.xpath('.//div[@class="reviewsCount"]//text()').string()
        if revs_count:
            revs_count = revs_count.strip('()')
            if int(revs_count) > 0:
                session.queue(Request(url), process_product, dict(context, name=name, url=url, ssid=ssid, brand=brand))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    prod_json = simplejson.loads(data.xpath("//script[contains(text(), '\"@type\": \"Product\"')]//text()").string())

    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.ssid = context['ssid']

    manufacturer = context.get('brand')
    if manufacturer:
        product.manufacturer = manufacturer

    ean = prod_json.get('gtin13')
    if ean:
        product.add_property(type='id.ean', value=ean)

    mpn = prod_json.get('mpn')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    revs_url = 'https://www.snowys.com.au/DbgReviews/ProductDetailsReviews?pagenumber=1&productId={ssid}&pageSize=5&orderBy=0&pictureSearch=0'.format(ssid=product.ssid)
    session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="product-reviews"]/following::body')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('div[@class="vote-options"]/@id').string().split('options-')[-1]
        review.title = rev.xpath('h4//text()').string()
        review.date = rev.xpath('.//span[@class="date"]//text()').string()

        author = rev.xpath('div[@class="customer-name"]/span[1]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[@class="rating"]/span//text()').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.xpath('.//input[@title="Upvote"]/@value').string()
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//input[@title="Downvote"]/@value').string()
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        excerpt = rev.xpath('p//text() | span//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)
            product.reviews.append(review)

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.do(Request(next_url), process_reviews, dict(product=product))
    else:
        session.emit(product)
