from agent import *
from models.products import *

import simplejson


XCAT = ['Outdoor Equipment', 'Brands', 'Sale']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.luggage.co.nz/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[@class="group inline-block"]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('.//div[contains(@class, "mb-2 w-1/5")]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('span[contains(@class, "block p-2")]/text()').string()
                url = cat.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="item column small-6 medium-4 large-3"]')
    for prod in prods:
        name = prod.xpath('div[@class="product-name"]/a//text()').string()
        url = prod.xpath('div[@class="product-name"]/a/@href').string().split('?')[0]

        revs_count = prod.xpath('.//div[@class="reviews"]//span[@class="count"]//text()').string()
        if revs_count:
            revs_count = revs_count.split(' Review')[0]
            if int(revs_count) > 0:
                session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@class="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    prod_json = simplejson.loads(data.xpath("//script[contains(text(), '\"@type\": \"Product\"')]//text()").string())

    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.manufacturer = prod_json.get('brand')
    product.ssid = data.xpath('//div[@class="stamped stamped-main-widget"]/@data-product-id').string()
    
    mpn = prod_json.get('sku')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    revs_url = "https://stamped.io/api/widget?productId={ssid}&page=1&apiKey=pubkey-UuS0y874990W7wl8Gr8V8xQ8Hw4g26&storeUrl=www.luggage.co.nz&take=5".format(ssid=product.ssid)
    session.do(Request(revs_url), process_reviews, dict(product=product, page=1))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    new_data = data.parse_fragment(revs_json['widget'])

    revs = new_data.xpath("//div[@class='stamped-review']")
    for rev in revs:
        review = Review()
        review.title = rev.xpath(".//div[@class='stamped-review-body']/h3[@class='stamped-review-header-title']//text()").string()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath(".//div[@class='created']//text()").string()
        review.ssid = rev.xpath("@id").string().split('review-')[-1]
        
        author_name = rev.xpath(".//strong[@class='author']//text()").string()
        review.authors.append(Person(name=author_name, ssid=author_name))
        
        grade_overall = rev.xpath("@data-rating").string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))
        
        is_verified = rev.xpath('.//span[@class="stamped-verified-badge"]/@data-verified-label')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)
        else:
            continue

        hlp_yes = rev.xpath('.//i[@class="stamped-fa stamped-fa-thumbs-up"]//text()').string()
        if hlp_yes:
            hlp_yes = int(hlp_yes.split('sp;')[-1])
            review.add_property(type='helpful_votes', value=int(hlp_yes))
        
        hlp_no = rev.xpath('.//i[@class="stamped-fa stamped-fa-thumbs-down"]//text()').string()
        if hlp_no:
            hlp_no = int(hlp_no.split('sp;')[-1])
            review.add_property(type='not_helpful_votes', value=int(hlp_no))
  
        excerpt = rev.xpath(".//div[@class='stamped-review-body']/p[@class='stamped-review-content-body']//text()").string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    next_page = new_data.xpath('//li[@class="next"]/a/@data-page').string()
    if next_page and int(next_page) > context['page']:
        next_url = "https://stamped.io/api/widget?productId={ssid}&page={page}&apiKey=pubkey-UuS0y874990W7wl8Gr8V8xQ8Hw4g26&storeUrl=www.luggage.co.nz&take=5".format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url), process_reviews, dict(product=product, page=int(next_page)))
    elif product.reviews:
        session.emit(product)
        
