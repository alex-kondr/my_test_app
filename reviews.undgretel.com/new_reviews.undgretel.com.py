from agent import *
from models.products import *
import simplejson


XCAT = ['Gutscheine']


def run(context, session):
    session.queue(Request('https://undgretel.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//span[contains(., "Products")]/following-sibling::ul[@class="flex flex-col mb-4"]//a')
    for cat in cats[::-1]:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="col-span-1 wow animate__fadeIn"]')
    for prod in prods:
        name = prod.xpath('.//div[@class="pt-4 px-4 text-[22px] font-normal mb-1 text-black"]/text()').string()
        url = prod.xpath('.//a[@class="block overflow-hidden group grow empty:bg-gray-100"]/@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat']
###########
    prod_json = data.xpath('''//script[contains(., '"product": {"id":')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('@graph', [{}])[0].get('manufacturer', {}).get('name')

        ean = prod_json.get('@graph', [{}])[0].get('gtin13')
        if ean and ean.isdigit() and len(ean) > 12:
            product.add_property(type='id.ean', value=ean)

    revs_cnt = data.xpath('//div[contains(text(), "Reviews")]/text()').string()
    if revs_cnt and int(revs_cnt.replace('Reviews', '')) > 0:
        context['product'] = product

        process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="jdgm-rev jdgm-divider-top"]')######
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//time/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//strong[@class="woocommerce-review__author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span/@style').string()
        if grade_overall:
            grade_overall = float(grade_overall.replace('width:', '').replace('%', '')) / 20
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//div[@class="description"]/p//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
