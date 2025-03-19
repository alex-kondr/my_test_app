from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.mattenlager.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="mobile-nav-content"]/ul/li')
    for cat in cats:
        name = cat.xpath('span//a/text()').string()

        sub_cats = cat.xpath('ul/li//a')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = sub_cat.xpath('@href').string()
            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//li[@data-product-item="data-product-item"]')
    for prod in prods:
        name = prod.xpath('.//a[@data-product-page-link="data-product-page-link" and not(@class)]/text()').string()
        url = prod.xpath('.//a[@data-product-page-link="data-product-page-link" and not(@class)]/@href').string()

        revs_cnt = prod.xpath('.//div/@data-number-of-reviews').string()
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

# No next page


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div[contains(@class, "preview-badge")]/@data-id').string()
    product.category = context['cat']
    product.manufacturer = 'Mattenlager'

    prod_json = data.xpath('''//script[contains(., '"@type": "Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.sku = str(prod_json.get('mpn'))

        mpn = prod_json.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

    revs_url = 'https://api.judge.me/reviews/reviews_for_widget?url=mattenlager.myshopify.com&shop_domain=mattenlager.myshopify.com&platform=shopify&page=1&per_page=5&product_id={}'.format(product.ssid)
    session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs_html = data.parse_fragment(revs_json.get('html'))

    revs = revs_html.xpath('//div[@class="jdgm-rev jdgm-divider-top"]')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.ssid = rev.xpath('@data-review-id').string()

        date = rev.xpath('.//span[contains(@class, "timestamp")]/@data-content').string()
        if date:
            review.date = date.split()[0]

        author = rev.xpath('.//span[@class="jdgm-rev__author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span/@data-score').string()
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.xpath('@data-verified-buyer').string()
        if is_verified_buyer == 'true':
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.xpath('@data-thumb-up-count').string()
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('@data-thumb-down-count').string()
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.xpath('.//b[@class="jdgm-rev__title"]/text()').string()
        excerpt = rev.xpath('.//div[contains(@class, "rev__body")]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)

    revs_cnt = revs_json.get('total_count')
    offset = context.get('offset', 0) + 5
    if offset < int(revs_cnt):
        next_page = context.get('page', 1) + 1
        next_url = 'https://api.judge.me/reviews/reviews_for_widget?url=mattenlager.myshopify.com&shop_domain=mattenlager.myshopify.com&platform=shopify&page={page}&per_page=5&product_id={ssid}'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url), process_reviews, dict(product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
