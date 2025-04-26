from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=9000)]
    session.queue(Request("https://www.snowys.com.au/", use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[ul[@class="home-subcategory-list"]]')
    for cat in cats:
        name = cat.xpath('a//text()').string()

        sub_cats = cat.xpath('ul[@class="home-subcategory-list"]/li')
        if sub_cats:
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a//text()').string()

                sub_cats1 = sub_cat.xpath('ul[@class="home-subsubcategory-list"]/li/a')
                if sub_cats1:
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('.//text()').string(multiple=True)
                        url = sub_cat1.xpath('@href').string()
                        session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                else:
                    url = sub_cat.xpath('a/@href').string()
                    session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name))
        else:
            url = cat.xpath('a/@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-item")]')
    for prod in prods:
        url = prod.xpath('.//a[@class="product-linksubarea"]/@href').string()
        ssid = prod.xpath('@data-productid').string()

        revs_cnt = prod.xpath('.//div[@class="reviewsCount"]//text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, url=url, ssid=ssid))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = data.xpath('//div[@class="product-name"]/h1/text()').string()
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = data.xpath('//div[contains(@id, "sku")]/text()').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[@class="product-name"]/h2//text()').string(multiple=True)

    mpn = data.xpath('//div[contains(@id, "mpn")]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    prod_json = data.xpath('''//script[contains(text(), '"@type": "Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json.replace('	', '').replace('\&', ''))

        ean = prod_json.get('gtin13')
        if ean:
            product.add_property(type='id.ean', value=str(ean))

    revs_url = 'https://www.snowys.com.au/DbgReviews/ProductDetailsReviews/?pagenumber=1&productId={}&pageSize=5&orderBy=0'.format(product.ssid)
    session.do(Request(revs_url, use='curl', force_charset='utf-8'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="product-review-item"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
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

        title = rev.xpath('h4//text()').string(multiple=True)
        excerpt = rev.xpath('p//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            ssid = rev.xpath('div[contains(@class, "vote-options")]/@id').string()
            if ssid:
                review.ssid = ssid.split('options-')[-1]
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.do(Request(next_url, use='curl', force_charset='utf-8'), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
