from agent import *
from models.products import *
import simplejson


XCAT = ['All Products']


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request("https://www.majority.co.uk/products/"), process_catlist, dict())

def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class="standard"]/li/a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//li[contains(@class, "product card")]')
    for prod in prods:
        name = prod.xpath('h3/text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    strip_namespace(data)

    product = context.get('product')
    if not product:
        product = Product()
        product.name = context['name']
        product.category = context['cat']
        product.url = context['url']
        product.manufacturer = 'Majority'

    prod_json = simplejson.loads(data.xpath('//script[contains(text(), "var dataLayer_content")]//text()').string().replace('var dataLayer_content = ', '').replace('; dataLayer.push( dataLayer_content );', ''))
    prod_info = prod_json.get('ecommerce', {}).get('detail', {}).get('products')
    if prod_info:
        product.ssid = str(prod_info[0]['id'])
        product.sku = str(prod_info[0]['sku'])
    else:
        product.ssid = str(prod_json['ecomm_prodid'])
        prod_json_2 = simplejson.loads(data.xpath('//form/@data-product_variations').string())
        product.sku = str(prod_json_2[0]['sku'])

    revs = data.xpath('//div[@class="comment_container"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@id').string().split('-')[-1]

        title = rev.xpath('.//h3[@class="contribution-title review-title"]/span//text()').string()
        if title:
            review.title = title.encode("ascii", errors="ignore")

        date = rev.xpath('.//time[@class="woocommerce-review__published-date"]/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//strong[@class="woocommerce-review__author"]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        hlp_yes = rev.xpath('.//span[@class="vote-count vote-count-positive"]/span/text()').string()
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//span[@class="vote-count vote-count-negative"]/span/text()').string()
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        grade_overall = rev.xpath('.//strong[@class="rating"]/text()').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//div[@class="description"]/p//text()').string(multiple=True)
        if excerpt:
            excerpt = excerpt.encode("ascii", errors="ignore")
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    next_url = data.xpath('//a[@class="next page-numbers"]/@href').string()
    if next_url:
        session.do(Request(next_url), process_product, dict(product=product))

    elif product.reviews:
        session.emit(product)
