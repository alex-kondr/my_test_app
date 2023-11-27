from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request("https://store.blackview.hk"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('(//div[@class="menu_footer widget_footer"])[1]/ul/li[position() < last()]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//h3[@class="product-title pr fs__14 mg__0 fwm"]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product = Product()

    prod_json = simplejson.loads(data.xpath('(//script[@type="application/ld+json"])[1]//text()').string().replace('\\', '/'))

    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.manufacturer = 'Blackview'
    product.ssid = prod_json["@id"]
    product.sku = prod_json["sku"]

    mpn = prod_json["mpn"]
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    revs_count = prod_json.get("aggregateRating", {}).get("reviewCount")
    if revs_count and int(revs_count) > 0:
        revs_url = "https://productreviews.shopifycdn.com/proxy/v4/reviews?callback=paginateCallback{ssid}&page={page}&product_id={ssid}&shop=blackview-store.myshopify.com&product_ids[]={ssid}".format(ssid=product.ssid, page=1)
        session.do(Request(revs_url, force_charset='utf-8'), process_reviews, dict(product=product, page=1, revs_count=revs_count))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads('{"remote_id"' + data.content.split('({"remote_id"')[-1].rstrip(')'))

    new_data = data.parse_fragment(revs_json['reviews'])

    revs = new_data.xpath('//div[@class="spr-review"]')
    for rev in revs:
        review = Review()

        review.type = 'user'
        review.url = product.url

        title = rev.xpath('.//h3//text()').string()
        if title:
            review.title = title.encode().decode()

        ssid = rev.xpath('@id').string()
        if ssid:
            review.ssid = ssid.split('view-')[-1]

        rev_content = rev.xpath('.//span[@class="spr-review-header-byline"]//text()').string(multiple=True)
        if rev_content:
            review.date = rev_content.split(' on ')[-1]

            author = rev_content.split(' on ')[0]
            if author:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@class="spr-starratings spr-review-header-starratings"]/@aria-label').string()
        if grade_overall:
            grade_overall = float(grade_overall.split(' of ')[0])
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        excerpt = rev.xpath(".//p[@class='spr-review-content-body']//text()").string(multiple=True)
        if excerpt:
            excerpt = excerpt.encode().decode()
            review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)

    if int(context['revs_count']) <= 5 and product.reviews:
        session.emit(product)
    else:
        per_page = 5
        pages_count = int(context['revs_count']) // per_page
        if int(context['revs_count']) // per_page != 0:
            pages_count += 1
        page = context['page'] + 1
        if page <= pages_count:
            revs_url = "https://productreviews.shopifycdn.com/proxy/v4/reviews?callback=paginateCallback{ssid}&page={page}&product_id={ssid}&shop=blackview-store.myshopify.com&product_ids[]={ssid}".format(ssid=product.ssid, page=page)
            session.do(Request(revs_url), process_reviews, dict(context, product=product, page=page))
        else:
            session.emit(product)
