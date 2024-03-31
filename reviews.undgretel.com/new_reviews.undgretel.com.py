from agent import *
from models.products import *
import simplejson


XCAT = ['Gutscheine']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://undgretel.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//span[contains(., "Products")]/following-sibling::ul[@class="flex flex-col mb-4"]//a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_prodlist, dict(cat='Beauty' + '|' + name))


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
    product.manufacturer = 'UND GRETEL'

    prod_json = data.xpath('''//script[contains(., '"product": {"id":')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        ean = prod_json.get('product', {}).get('id')
        if ean:
            product.add_property(type='id.ean', value=ean)

        product.sku = prod_json.get('product', {}).get('variants', [{}])[0].get('sku')

    revs_cnt = data.xpath('//div[contains(text(), "Reviews")]/text()').string()
    if revs_cnt and int(revs_cnt.replace('Reviews', '').replace('.', '')) > 0:
        revs_url = 'https://judge.me/reviews/reviews_for_widget?url=undgretel.myshopify.com&shop_domain=undgretel.myshopify.com&platform=shopify&page=1&per_page=10&product_id={id}'.format(id=ean)
        session.do(Request(revs_url), process_reviews, dict(product=product, ean=ean))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    new_data = data.parse_fragment(revs_json.get('html'))

    revs = new_data.xpath('//div[@class="jdgm-rev jdgm-divider-top"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//span/@data-content').string()
        if date:
            review.date = date.split()[0]

        author = rev.xpath('.//span[@class="jdgm-rev__author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        is_verified_buyer = rev.xpath('.//span[@class="jdgm-rev__buyer-badge"]')
        if is_verified_buyer:
            review.add_property(type="is_verified_buyer", value=True)

        grade_overall = rev.xpath('.//span/@data-score').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.xpath('.//b[@class="jdgm-rev__title"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//div[@class="jdgm-rev__body"]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = rev.xpath('@data-review-id').string()
            if not review.ssid:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    next_page = new_data.xpath('//a[@rel="next"]/@data-page').string()
    if next_page:
        next_url = 'https://judge.me/reviews/reviews_for_widget?url=undgretel.myshopify.com&shop_domain=undgretel.myshopify.com&platform=shopify&page={next_page}&per_page=10&product_id={id}'.format(next_page=next_page, id=context['ean'])
        session.do(Request(next_url), process_reviews, dict(context, product=product))

    elif product.reviews:
        session.emit(product)
