from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Support']


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


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://koss.com/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//div[@data-navigation]/ul/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            subcats = cat.xpath('ul/li/a')
            for subcat in subcats:
                subcat_name = subcat.xpath('text()').string()
                url = subcat.xpath('@href').string()

                if not subcat_name.startswith("All "):
                    session.queue(Request(url), process_prodlist, dict(cat=name+'|'+subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//a[contains(@class, "product-item")]')
    for rev in revs:
        name = rev.xpath('@title').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="product-id"]/@value').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[contains(@class, "product__vendor")]/a/text()').string()

    try:
        prod_json = data.xpath('//script[contains(@id, "ProductJson")]/text()').string()
        prod_json = simplejson.loads(prod_json)

        product.sku = prod_json.get('variants', [{}])[0].get('sku')
    except:
        pass

    revs_cnt = data.xpath('//div/@data-number-of-reviews').string()
    if revs_cnt and revs_cnt.isdigit() and int(revs_cnt) > 0:
        revs_url = 'https://cdn.judge.me/reviews/reviews_for_widget?url=koss-stereophones.myshopify.com&shop_domain=koss-stereophones.myshopify.com&platform=shopify&page=1&per_page=5&product_id=' + product.ssid
        session.do(Request(revs_url), process_reviews, dict(product=product, revs_cnt=int(revs_cnt)))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = context['product']

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    new_data = data.parse_fragment(revs_json.get('html'))

    revs = new_data.xpath('//div[contains(@class, "reviews")]/div[@data-review-id]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@data-review-id').string()

        date = rev.xpath('.//time/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//span[contains(@class, "rev__author")]//text()').string(multiple=True)
        if author and 'anonymous' not in author.lower():
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span/@data-score').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.xpath('.//span[@class="jdgm-rev__buyer-badge"]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.xpath('.//b[contains(@class, "rev__title")]//text()').string(multiple=True)
        excerpt = rev.xpath('.//div[contains(@class, "rev__body")]/p//text()').string(multiple=True)
        if excerpt and len(remove_emoji(excerpt).strip()) > 2:
            if title:
                review.title = remove_emoji(title).strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        next_url = 'https://cdn.judge.me/reviews/reviews_for_widget?url=koss-stereophones.myshopify.com&shop_domain=koss-stereophones.myshopify.com&platform=shopify&page={page}&per_page=5&product_id={ssid}'.format(page=next_page, ssid=product.ssid)
        session.do(Request(next_url), process_reviews, dict(context, product=product, offset=offset,page=next_page))

    elif product.reviews:
        session.emit(product)
