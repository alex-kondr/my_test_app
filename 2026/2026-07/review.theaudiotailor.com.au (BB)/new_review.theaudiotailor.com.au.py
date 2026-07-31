from agent import *
from models.products import *
import simplejson
import time
import random


XCAT = ['Certified Pre-Owned']


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.theaudiotailor.com.au/', force_charset='utf-8'), process_frontpage, {})


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    cats = data.xpath('//li[contains(@class, "category")]/ul/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            subcats = cat.xpath('ul/li/a')
            for subcat in subcats:
                subcat_name = subcat.xpath('text()').string()
                url = subcat.xpath("@href").string()
                session.queue(Request(url, force_charset='utf-8'), process_prodlist, dict(cat=name+'|'+subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    prods = data.xpath('//div[@class="productitem--info"]')
    for prod in prods:
        name = prod.xpath('h2/a/text()').string()
        slug = prod.xpath('h2/a/@href').string().split('/')[-1]
        url = 'https://www.theaudiotailor.com.au/products/' + slug
        if not session.seen(url):
        session.queue(Request(url, force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="product-id"]/@value').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[@class="product-vendor"]/a/text()').string()

    prod_json = data.xpath("""//script[contains(., '"@type": "Product"')]/text()""").string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        mpn = prod_json.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('mpn')
        if ean and str(ean).isdigit() and len(str(ean)) > 10:
            product.add_property(type='id.ean', value=str(ean))

    revs_cnt = data.xpath('//p[@class="rating__count"]/span/text()').string()
    if revs_cnt:
        revs_cnt = int(revs_cnt.split()[0])
        if revs_cnt > 0:
            reviews_url = 'https://stamped.io/api/widget?productId={ssid}&page=1&apiKey=pubkey-4uAqjKnE59XZzn681fYPnqd9x5pk1x&sId=24507&take=5'.format(ssid=product.ssid)
            session.do(Request(reviews_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, revs_cnt=revs_cnt))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    product = context['product']

    try:
        html = simplejson.loads(data.content).get('widget', '')
    except:
        html = ''

    revs_html = data.parse_fragment(html)

    revs = revs_html.xpath('//div[@class="stamped-review"]')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.date = rev.xpath('.//div[@class="created"]/text()').string()

        author = rev.xpath('.//strong[@class="author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('@data-rating').string()
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//span[@data-verified-label="Verified Buyer"]')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.xpath('.//h3[contains(@class, "title")]/text()').string()
        excerpt = rev.xpath('.//p[contains(@class, "content-body")]/text()').string(multiple=True)
        if excerpt and len(excerpt.replace('\n', '').replace('\t', '').strip()) > 2:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.replace('\n', '').replace('\t', '').strip()
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                ssid = rev.xpath('@id').string()
                if ssid:
                    review.ssid = ssid.split('-')[-1]
                else:
                    review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        next_url = 'https://stamped.io/api/widget?productId={ssid}&page={page}&apiKey=pubkey-4uAqjKnE59XZzn681fYPnqd9x5pk1x&sId=24507&take=5'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url, force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
