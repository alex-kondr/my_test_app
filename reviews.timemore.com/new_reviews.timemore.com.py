from agent import *
from models.products import *
import simplejson

XCAT = ['About Us', 'Contact Us', 'Where to Buy', 'Best Sellers', 'The Gift']


def remove_emoji(string):
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002500-\U00002BEF"  # chinese char
                               u"\U00002702-\U000027B0"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.timemore.com/', force_charset='utf-8'), process_catlist, {})


def process_catlist(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//li[contains(@class, "site-nav")]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if url and name and name not in XCAT:
            session.queue(Request(url, force_charset='utf-8'), process_prodlist, dict(cat=name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//div[contains(@class, "grid__item grid-product")]')
    for prod in prods:
        name = prod.xpath('.//div[contains(@class, "title")]/text()').string()
        url = prod.xpath('.//a[@class="grid-product__link"]/@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_product, dict(context, name=name, url=url))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div[@class="product-section"]/@data-product-id').string()
    product.category = context['cat']
    product.manufacturer = 'TIMEMORE'

    try:
        prod_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
        prod_json = simplejson.loads(prod_json)

        product.sku = prod_json.get('sku')

        ean = prod_json.get('gtin14')
        if ean and str(ean).isdigit() and len(str(ean)) > 10:
            product.add_property(type='id.ean', value=ean)
    except:
        pass

    try:
        revs_cnt_json = data.xpath('//script[contains(., "reviewCount")]/text()').string()
        context['revs_cnt'] = revs_cnt_json.get('aggregateRating', {}).get('reviewCount')
    except:
        pass

    if product.ssid:
        revs_url = "https://judge.me/reviews/reviews_for_widget?url=timemore-re.myshopify.com&shop_domain=timemore-re.myshopify.com&platform=shopify&page=1&per_page=10&product_id=" + product.ssid
        session.do(Request(revs_url, max_age=0, force_charset='utf-8'), process_reviews, dict(context, product=product))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context["product"]

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('reviews', [])
    for rev in revs:
        review = Review()
        review.url = product.url
        review.type = 'user'
        review.ssid = rev.get('uuid')

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('reviewer_name')
        if author:
            author = remove_emoji(author).strip()
            if len(author) > 1:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.get('verified_buyer')
        if is_verified is True:
            review.add_property(type='is_verified_buyer', value=is_verified)

        hlp_yes = rev.get('thumb_up')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('thumb_down')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.get('title')
        excerpt_html = rev.get('body_html')
        excerpt = data.parse_fragment(excerpt_html).xpath('.//text()').string(multiple=True)
        if excerpt and len(remove_emoji(excerpt).replace('\n', '').replace('\r', '').strip()) > 2:
            if title:
                review.title = remove_emoji(title).strip()
        else:
            excerpt = title

        if excerpt:
            if '{"number_of_reviews"' in excerpt:
                excerpt = excerpt_html

            excerpt = remove_emoji(excerpt).replace('\n', '').replace('\r', '').replace('<p>', '').replace('</p>', '').replace('<a>', '').replace('</a>', '').strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = context.get('revs_cnt', revs_json.get('number_of_reviews', 0))
    offset = context.get('offset', 0) + 10
    if offset < revs_cnt:
        next_page = context.get("page", 1) + 1
        next_url = "https://judge.me/reviews/reviews_for_widget?url=timemore-re.myshopify.com&shop_domain=timemore-re.myshopify.com&platform=shopify&page={page}&per_page=10&product_id=={ssid}".format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url, max_age=0, force_charset='utf-8'), process_reviews, dict(product=product, offset=offset, page=next_page, revs_cnt=revs_cnt))

    elif product.reviews:
        session.emit(product)
