from agent import *
from models.products import *
import simplejson


XCAT = ['Sonos Shop', 'Help & Advice', 'Blog', 'Clearance']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.smarthomesounds.co.uk/', use="curl", force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//a[@class="level-top"]')
    for cat in cats:
        name = cat.xpath('span/text()').string()
        url = cat.xpath('@href').string()
        if name not in XCAT:
            session.queue(Request(url, use="curl", force_charset='utf-8'), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//a[@class="product-item-link"]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        if name and url:
            session.queue(Request(url, use="curl", force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use="curl", force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]

    ean = data.xpath('//@data-flix-ean').string()
    if ean:
        product.properties.append(ProductProperty(type='id.ean', value=ean))

    prod_data = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
    if prod_data:
        prod_data = simplejson.loads(prod_data)

        product.manufacturer = prod_data.get('brand', {}).get('name')

        mpn = prod_data.get('sku')
        if mpn:
            product.properties.append(ProductProperty(type='id.manufacturer', value=str(mpn)))

            url = 'https://api.reviews.co.uk/product/review?&store=smart-home-sounds&sku={}&per_page=10000'.format(mpn)
            session.do(Request(url, use="curl", force_charset='utf-8', max_age=0), process_reviews, dict(product=product))

    if product.reviews:
        session.emit(product)


def process_reviews(data, context, session):
    product = context["product"]

    info = simplejson.loads(data.content)
    revs = info.get("reviews", {}).get('data', [])
    for rev in revs:
        review = Review()
        review.title = rev.get('title')
        review.url = product.url
        review.ssid = str(rev['product_review_id'])
        review.type = "user"

        date = rev.get('date_created')
        if date:
            review.date = date.split(' ')[0]

        author = rev.get('reviewer')
        if author:
            author_name = author.get('first_name', '') + " " + author.get('last_name', '')
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
            excerpt = excerpt.replace("\r", "").replace("\n", "").encode("ascii", errors="ignore").strip()
            if excerpt:
                review.add_property(type="excerpt", value=excerpt)
                product.reviews.append(review)
