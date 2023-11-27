from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=9000)]
    session.queue(Request("https://www.snowys.com.au/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[ul[@class="home-subcategory-list"]]')
    for cat in cats:
        name = cat.xpath('a//text()').string()

        sub_cats = cat.xpath('ul[@class="home-subcategory-list"]/li')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('a//text()').string()

            sub_cats1 = sub_cat.xpath('ul[@class="home-subsubcategory-list"]/li/a')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('.//text()').string(multiple=True)
                url = sub_cat1.xpath('@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
            else:
                url = sub_cat.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))
        else:
            url = cat.xpath('a/@href').string()
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-item"]')
    for prod in prods:
        name = prod.xpath('.//span[@class="productName"]//text()').string()
        url = prod.xpath('.//a[@class="product-linksubarea"]/@href').string()
        ssid = prod.xpath('@data-productid').string()
        manufacturer = prod.xpath('.//span[@class="brandName"]//text()').string()

        revs_cnt = prod.xpath('.//div[@class="reviewsCount"]//text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url, ssid=ssid, manufacturer=manufacturer))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.ssid = context['ssid']
    product.manufacturer = context.get('manufacturer')

    prod_json = data.xpath('''//script[contains(text(), '"@type": "Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json.replace('	', '').replace('\&', ''))

        ean = prod_json.get('gtin13')
        if ean:
            product.add_property(type='id.ean', value=ean)

        mpn = prod_json.get('mpn')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

    revs_url = 'https://www.snowys.com.au/DbgReviews/ProductDetailsReviews?pagenumber=1&productId=' + product.ssid
    session.do(Request(revs_url, max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//body[div[@class="customer-review"]]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.title = rev.xpath('h4//text()').string(multiple=True)
        review.date = rev.xpath('.//span[@class="date"]/@content').string()

        author = rev.xpath('div[@class="customer-name"]/span/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[@class="rating"]/span//text()').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.xpath('.//input[@title="Upvote"]/@value').string()
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//input[@title="Downvote"]/@value').string()
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        excerpt = rev.xpath('p//text() | span//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            ssid = rev.xpath('div[@class="vote-options"]/@id').string()
            if ssid:
                review.ssid = ssid.split('options-')[-1]
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.do(Request(next_url), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
