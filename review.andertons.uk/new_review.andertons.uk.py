from agent import *
from models.products import *
import simplejson


XCAT = ["Offers", "Brands"]
KEY = 'key_A2YIqKz8zkXkA26G'


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.andertons.co.uk/sitemap/categories'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//h2[contains(., "Categories")]/following-sibling::ul/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('ul/li')

            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a/text()').string()
                if name != sub_name:
                    sub_name = name + '|' + sub_name

                url = sub_cat.xpath('a/@href').string()

                sub_cats1 = sub_cat.xpath('ul/li/a')
                if sub_cats1:
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath("text()").string()
                        url = sub_cat1.xpath("@href").string()
                        if url and '/browse/' in url:
                            url = url[:-1].replace('https://www.andertons.co.uk/browse/', 'https://ac.cnstrc.com/browse/group_id/browse/') + '?key={key}&page=1&num_results_per_page=96'.format(key=KEY)
                            session.queue(Request(url), process_prodlist, dict(cat=sub_name + '|' + sub_name1, prods_url=url))

                elif url and '/browse/' in url:
                    url = url[:-1].replace('https://www.andertons.co.uk/browse/', 'https://ac.cnstrc.com/browse/group_id/browse/') + '?key={key}&page=1&num_results_per_page=96'.format(key=KEY)
                    session.queue(Request(url), process_prodlist, dict(cat=sub_name, prods_url=url))


def process_prodlist(data, context, session):
    prods_json = simplejson.loads(data.content)
    if prods_json:

        prods = prods_json.get('response', {}).get('results', [])
        for prod in prods:
            product = Product()
            product.name = prod.get('value')
            product.url = 'https://www.andertons.co.uk' + prod.get('data', {}).get('url')
            product.ssid = prod.get('data', {}).get('url').replace('/', '')
            product.category = context['cat']
            product.manufacturer = prod.get('data', {}).get('brand')

            sku = prod.get('data', {}).get('productId')
            if sku:
                product.sku = str(sku)

            mpn = prod.get('data', {}).get('id')
            revs_cnt = prod.get('data', {}).get('reviewCount')
            if mpn and revs_cnt and int(revs_cnt) > 0:
                product.add_property(type='id.manufacturer', value=mpn)

                revs_url = 'https://api.feefo.com/api/10/reviews/product?page=1&page_size=100&since_period=ALL&full_thread=include&unanswered_feedback=include&source=on_page_product_integration&sort=-updated_date&feefo_parameters=include&media=include&merchant_identifier=andertons-music&origin=www.andertons.co.uk&product_sku={mpn}&translate_attributes=exclude%20%20%20%20&empty_reviews=true'.format(mpn=mpn)
                session.do(Request(revs_url), process_reviews, dict(product=product, mpn=mpn))

        prods_cnt = prods_json.get('response', {}).get('total_num_results', 0)
        offset = context.get('offset', 0) + 96
        if offset < prods_cnt:
            page = context.get('page', 1)
            next_url = context.get('prods_url').replace('&page=' + str(page), '&page=' + str(page+1))
            session.queue(Request(next_url), process_prodlist, dict(context, offset=offset, page=page+1))


def process_reviews(data, context, session):
    product = context['product']

    data_json = simplejson.loads(data.content)
    revs = data_json.get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('products', [{}])[0].get('id')

        date = rev.get('products', [{}])[0].get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('customer', {}).get('display_name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('products', [{}])[0].get('rating', {}).get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        grades = rev.get('products', [{}])[0].get('attributes', [])
        for grade in grades:
            grade_name = grade.get('name')
            grade_val = grade.get('rating')
            if grade_name and grade_val:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

        hlp_yes = rev.get('products', [{}])[0].get('helpful_votes')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        excerpt = rev.get('products', [{}])[0].get('review')
        if excerpt:
            excerpt = excerpt.replace(u'\ud83d', '').replace(u'\ude0d', '').replace(u'\udc4d', '').strip(' +-.,')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = data_json.get('summary', {}).get('meta', {}).get('count', 0)
    offset = context.get('offset', 0) + 100
    if offset < revs_cnt:
        mpn = context['mpn']
        next_url = 'https://api.feefo.com/api/10/reviews/product?page=1&page_size=100&since_period=ALL&full_thread=include&unanswered_feedback=include&source=on_page_product_integration&sort=-updated_date&feefo_parameters=include&media=include&merchant_identifier=andertons-music&origin=www.andertons.co.uk&product_sku={mpn}&translate_attributes=exclude%20%20%20%20&empty_reviews=true'.format(mpn=mpn)
        session.do(Request(next_url), process_reviews, dict(product=product, mpn=mpn, offset=offset))

    elif product.reviews:
        session.emit(product)
