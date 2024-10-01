from agent import *
from models.products import *
import simplejson


XCAT = ["Offers", "Brands"]


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
                        if url:
                            url = url.replace('https://www.andertons.co.uk/browse/', 'https://ac.cnstrc.com/browse/group_id/browse/') + '?key=key_A2YIqKz8zkXkA26G&page=1&num_results_per_page=96'
                            session.queue(Request(url), process_prodlist, dict(cat=sub_name + '|' + sub_name1, prods_url=url))
                elif url:
                    url = url.replace('https://www.andertons.co.uk/browse/', 'https://ac.cnstrc.com/browse/group_id/browse/') + '?key=key_A2YIqKz8zkXkA26G&page=1&num_results_per_page=96'
                    session.queue(Request(url), process_prodlist, dict(cat=sub_name, prods_url=url))


def process_prodlist(data, context, session):
    prods_json = simplejson.loads(data.content)
    if prods_json:

        prods = prods_json.get('response', {}).get('results', [])
        for prod in prods:
            name = prod.get('value')
            url = 'https://www.andertons.co.uk' + prod.get('data', {}).get('url')

            revs_cnt = prod.get('data', {}).get('reviewCount')
            if revs_cnt and int(revs_cnt) > 0:
                session.queue(Request(url), process_product, dict(context, name=name, url=url))

        prods_cnt = prods_json.get('response', {}).get('total_num_results', 0)
        offset = context.get('offset', 0) + 96
        if offset < prods_cnt:
            page = context.get('page', 1)
            next_url = context.get('prods_url').replace('&page=' + str(page), '&page=' + str(page+1))
            session.queue(Request(next_url), process_prodlist, dict(context, offset=offset, page=page+1))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.ssid = product.url.split('/')[-1]

    mpn = data.xpath('//p[@class="o-part-number" and contains(text(), "SKU:")]/text()').string()
    if mpn:
        mpn = mpn.replace('SKU:', '').strip()
        product.add_property(type='id.manufacturer', value=mpn)

        revs_url = 'https://api.feefo.com/api/10/reviews/product?page=1&page_size=5&since_period=ALL&full_thread=include&unanswered_feedback=include&source=on_page_product_integration&sort=-updated_date&feefo_parameters=include&media=include&merchant_identifier=andertons-music&origin=www.andertons.co.uk&product_sku={mpn}&translate_attributes=exclude%20%20%20%20&empty_reviews=true'.format(mpn=mpn)
        session.queue(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = simplejson.loads(data.context).get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('products', [{}])[0].get('id')
        review.date = rev.get('products', [{}])[0].get('created_at')

        author = rev.xpath('.//p[@class="o-customer-review__name"]/span/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[@class="o-review-stars"]/@title').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        grades = rev.xpath('.//p[@class="o-customer-review__rating"]/span')
        if grades:
            for grade in grades:
                name_value = grade.xpath("text()").string()
                if name_value:
                   name = name_value.split(" ")[0]
                   value = float(name_value.split(" ")[1])
                   review.grades.append(Grade(name=name, value=value, best=5.0))

        excerpt = rev.xpath('text()').string()
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # no next page, all revs loaded on prod's page
