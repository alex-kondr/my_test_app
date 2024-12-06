from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.apothema.gr/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@class="dropdown"]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        sub_cats = cat.xpath('.//div[@class="col"]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('h3//text()').string(multiple=True)

            sub_cats1 = sub_cat.xpath('.//li/a')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('text()').string()
                url = sub_cat1.xpath('@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat = name + '|' + sub_name + '|' + sub_name1))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product__item")]')
    for prod in prods:
        name = prod.xpath('.//span[@class="product__title"]/a/text()').string()
        url = prod.xpath('.//span[@class="product__title"]/a/@href').string()

        revs_cnt = prod.xpath('.//div[@class="reviews_count"]/text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@title="Επόμενη σελίδα"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]
    product.category = context['cat']

    prod_json = data.xpath("""//script[contains(., '"@type": "Product"')]/text()""").string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')

        product.sku = prod_json.get('sku')

        mpn = prod_json.get('mpn')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//div/@data-loadbee-gtin').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[contains(@class, "reviews__panel")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//p[contains(@class, "info")]/text()').string()
        if date:
            review.date = date.split()[-1]

        author = rev.xpath('.//p[contains(@class, "info")]/strong/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[contains(@class, "rating__total")]/text()').string()
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.xpath('.//a[i[@data-feather="thumbs-up"]]/text()').string()
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//a[i[@data-feather="thumbs-down"]]/text()').string()
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.xpath('.//h3[contains(@class, "title")]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[contains(@class, "item__text")]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
