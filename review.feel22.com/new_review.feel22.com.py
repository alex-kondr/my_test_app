from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    cats_links = ['makeup', 'skin-care', 'perfumes-1', 'hair-1', 'bath-body-1', 'nails', 'men-collection', 'kids-babies']
    for link in cats_links:
        url = 'https://www.searchanise.com/getresults?api_key=7I9N0F6L4v&q=&sortBy=total_reviews&sortOrder=desc&startIndex=0&maxResults=250&collection={link}&output=jsonp'.format(link=link)
        session.queue(Request(url, max_age=0), process_prodlist, dict(link=link))


def process_prodlist(data, context, session):
    try:
        prods_json = simplejson.loads(data.content)
    except:
        prods_json = {}

    prods = prods_json.get('items', [])
    for prod in prods:
        product = Product()
        product.name = prod.get('title')
        product.url = 'https://feel22.com' + prod.get('link')
        product.ssid = prod.get('product_id')
        product.sku = prod.get('product_code')
        product.category = prods_json.get('shopify_collection', {}).get('title', '').rstrip('.')
        product.manufacturer = prod.get('vendor')

        revs_cnt = prod.get('total_reviews')
        if revs_cnt and int(revs_cnt) > 0:
            revs_url = 'https://stamped.io/api/widget?productId={ssid}&apiKey=pubkey-9DajnAm17lctkg5Q1Jn859D09iIcT8&storeUrl=glam22.myshopify.com&take=5&sort=most-votes'.format(ssid=product.ssid)
            session.queue(Request(revs_url, max_age=0), process_reviews, dict(product=product, revs_cnt=int(revs_cnt)))

    prods_count = context.get('prods_count', prods_json.get('totalItems', 0))
    offset = context.get('offset', 0) + 250
    if offset < prods_count:
        next_url = 'https://www.searchanise.com/getresults?api_key=7I9N0F6L4v&q=&sortBy=total_reviews&sortOrder=desc&startIndex={start}&maxResults=250&collection={link}&output=jsonp'.format(start=offset, link=context['link'])
        session.queue(Request(next_url, max_age=0), process_prodlist, dict(context, offset=offset, prods_count=prods_count))


def process_reviews(data, context, session):
    product = context['product']

    if product.sku:
        product.sku = product.sku.split('SKU-')[-1]

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    new_data = data.parse_fragment(revs_json.get('widget', ''))

    revs = new_data.xpath('//div[@class="stamped-review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//div[@class="created"]//text()').string()

        author = rev.xpath('.//strong[@class="author"]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@class="stamped-starratings stamped-review-header-starratings"]/@data-rating').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//span[@data-type="buyer"]/@data-verified-label').string()
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)
        else:
            continue

        is_recommended = rev.xpath('.//div[@class="stamped-review-recommend"]/@data-is-recommend').string()
        if is_recommended == "true":
            review.add_property(value=True, type='is_recommended')

        hlp_yes = rev.xpath('.//i[@class="stamped-fa stamped-fa-thumbs-up"]//text()').string()
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//i[@class="stamped-fa stamped-fa-thumbs-down"]//text()').string()
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.xpath('.//h3[@class="stamped-review-header-title"]//text()').string()
        excerpt = rev.xpath('.//p[@class="stamped-review-content-body"]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.strip(' -.+*')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                ssid = rev.xpath('@id').string()
                if ssid:
                    review.ssid = ssid.split('-')[-1]
                else:
                    review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        next_url = 'https://stamped.io/api/widget?productId={ssid}&apiKey=pubkey-9DajnAm17lctkg5Q1Jn859D09iIcT8&storeUrl=glam22.myshopify.com&take=5&sort=most-votes&page={page}'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url, max_age=0), process_reviews, dict(context, product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
