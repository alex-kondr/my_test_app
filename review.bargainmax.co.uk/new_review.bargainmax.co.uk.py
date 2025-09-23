from agent import *
from models.products import *
import simplejson



def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request("https://www.bargainmax.co.uk/", use="curl", force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@data-menu-id="toys"]/div[@class="group/child"]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        sub_cats = cat.xpath('.//ul/li/a')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = sub_cat.xpath('@href').string()

            if 'View All' not in sub_name:
                session.queue(Request(url, use="curl", force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name+'|'+sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "ProductCard_productName")]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        if name and url:
            session.queue(Request(url, use="curl", force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use="curl", force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']

    revs_cnt = data.xpath('//span[contains(@class, "ProductRating_message")]/text()').string()
    if revs_cnt:
        revs_cnt = revs_cnt.replace('reviews', '').strip('() ')
        if not revs_cnt or int(revs_cnt) == 0:
            return

    prod_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
    if prod_json:
        prod_json = prod_json.replace('31" x 8"', '').replace(' 11" ', '')
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')

        ean = prod_json.get('gtin13')
        if ean:
            product.properties.append(ProductProperty(type='id.ean', value=str(ean)))

        product.sku = prod_json.get('sku')
        if product.sku:
            product.ssid = product.sku
            url = 'https://api.reviews.co.uk/product/review?store=bargainmax&sku={}&per_page=10000'.format(product.sku)
            session.do(Request(url, use="curl", force_charset='utf-8', max_age=0), process_reviews, dict(product=product))

    if product.reviews:
        session.emit(product)


def process_reviews(data, context, session):
    product = context["product"]

    try:
        info = simplejson.loads(data.content)
    except:
        return

    revs = info.get("reviews", {}).get('data')
    for rev in revs:
        review = Review()
        review.title = rev.get('title')
        review.url = product.url
        review.type = "user"

        date = rev.get('date_created')
        if date:
            review.date = date.split(' ')[0]

        ssid = str(rev.get('product_review_id'))
        if ssid:
            review.ssid = ssid

        author = rev.get('reviewer')
        if author:
            author_name = author.get('first_name', '') + ' ' + author.get('last_name', '')
            if author_name.strip():
                review.authors.append(Person(name=author_name, ssid=author_name))

        is_verified = rev.get('reviewer', {}).get('verified')
        if is_verified and 'yes' in is_verified.lower():
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('votes')
        if hlp_yes and hlp_yes > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        excerpt = rev.get('review')
        if excerpt:
            excerpt = excerpt.encode("ascii", errors="ignore").strip()
            if excerpt:
                review.add_property(type="excerpt", value=excerpt)

                product.reviews.append(review)
