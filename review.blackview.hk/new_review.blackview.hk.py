from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request("https://store.blackview.hk"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[@data-placement="bottom"]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//h3[@class="t4s-product-title"]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    prod_json = data.xpath('//script[@type="application/ld+json" and contains(., "@id")]//text()').string()
    if not prod_json:
        return

    prod_json = simplejson.loads(prod_json.replace('\\', '/'))

    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.manufacturer = 'Blackview'
    product.ssid = prod_json["@id"]
    product.sku = prod_json["sku"]

    mpn = prod_json["mpn"]
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    revs_cnt = prod_json.get("aggregateRating", {}).get("reviewCount")
    if revs_cnt and int(revs_cnt) > 0:
        revs_url = "https://productreviews.shopifycdn.com/proxy/v4/reviews?callback=paginateCallback{ssid}&page={page}&product_id={ssid}&shop=blackview-store.myshopify.com&product_ids[]={ssid}".format(ssid=product.ssid, page=1)
        session.do(Request(revs_url, force_charset='utf-8'), process_reviews, dict(product=product, page=1, revs_cnt=int(revs_cnt)))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = data.content.split('({"remote_id"')[-1].rstrip(')')
    if not revs_json:
        return

    revs_json = simplejson.loads('{"remote_id"' + revs_json)
    new_data = data.parse_fragment(revs_json['reviews'])

    revs = new_data.xpath('//div[@class="spr-review"]')
    for rev in revs:
        review = Review()

        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//span[@class="spr-review-header-byline"]/strong[2]/text()').string()

        title = rev.xpath('.//h3//text()').string(multiple=True)
        if title:
            review.title = title.encode().decode()

        ssid = rev.xpath('@id').string()
        if ssid:
            review.ssid = ssid.split('view-')[-1]

        author = rev.xpath('.//span[@class="spr-review-header-byline"]/strong[1]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@class="spr-starratings spr-review-header-starratings"]/@aria-label').string()
        if grade_overall:
            grade_overall = float(grade_overall.split(' of ')[0])
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        excerpt = rev.xpath(".//p[@class='spr-review-content-body']//text()").string(multiple=True)
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)

    revs_cnt = context['revs_cnt'] - 5
    if revs_cnt > 0:
        page = context['page'] + 1
        revs_url = "https://productreviews.shopifycdn.com/proxy/v4/reviews?callback=paginateCallback{ssid}&page={page}&product_id={ssid}&shop=blackview-store.myshopify.com&product_ids[]={ssid}".format(ssid=product.ssid, page=page)
        session.do(Request(revs_url, force_charset='utf-8'), process_reviews, dict(context, product=product, page=page, revs_cnt=revs_cnt))

    elif product.reviews:
        session.emit(product)
