from agent import *
from models.products import *
import simplejson
import re
import time
import random


XCAT = ['Offers', 'The Outdoor Shop', 'Outdoor Toys', 'Arts & Crafts']


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


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request("https://www.bargainmax.co.uk/", use='curl'), process_frontpage, dict())


def process_frontpage(data, context, session):
    time.sleep(random.uniform(1, 3))

    cats = data.xpath('//div[@class="group/child"]')
    for cat in cats:
        name = cat.xpath('button/text()').string()

        if name and name not in XCAT:
            cats1 = cat.xpath('.//div[contains(@id, "child-panel-sections")]')
            if cats1:
                for cat1 in cats1:
                    cat1_name = cat1.xpath('div/p[contains(@class, "h5")]/text()').string()

                    subcats = cat1.xpath('.//ul/li/a')
                    for subcat in subcats:
                        subcat_name = subcat.xpath('text()').string()
                        url = subcat.xpath('@href').string()

                        if subcat_name and subcat_name not in XCAT:
                            session.queue(Request(url, use='curl'), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
            else:
                cats1 = cat.xpath('.//div[nav]/a')
                for cat1 in cats1:
                    cat1_name = cat1.xpath('text()').string()
                    url = cat1.xpath('@href').string()

                    if cat1_name and cat1_name not in XCAT:
                        session.queue(Request(url, use='curl'), process_prodlist, dict(cat=name+'|'+cat1_name))


def process_prodlist(data, context, session):
    time.sleep(random.uniform(1, 3))

    prods = data.xpath('//div[ul]/div[contains(@class, "card-product")]/div[a and p]')
    for prod in prods:
        name = prod.xpath('p[contains(@class, "title")]/text()').string()
        url = prod.xpath('a/@href').string()

        rating = prod.xpath('p/span/span[contains(@class, "text")]/text()')
        if rating:
            session.queue(Request(url, use='curl'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_prodlist, dict(context))


def process_product(data, context, session):
    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//span[@class="product_id"]/text()').string()
    product.sku = data.xpath('//p[contains(strong/text(), "SKU:")]/text()').string(multiple=True)
    product.category = context['cat']

    prod_json = data.xpath('''//script[contains(., '"gtin":')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')

        ean = prod_json.get('gtin')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    sku_code = data.xpath('''//script[contains(., 'sku: "')]/text()''').string()
    if sku_code:
        sku_code = sku_code.split('sku: "')[-1].split('",')[0]

        revs_url = 'https://api.reviews.io/timeline/data?type=product_review&store=bargainmax&sort=date_desc&page=1&per_page=100&sku={}&enable_avatars=false&include_subrating_breakdown=1&must_have_comments=true&branch=&tag=&include_product_reviews=1&lang=en'.format(sku_code)
        session.do(Request(revs_url, use="curl", force_charset='utf-8', max_age=0), process_reviews, dict(product=product, sku_code=sku_code))


def process_reviews(data, context, session):
    product = context["product"]

    try:
        revs_json = simplejson.loads(data.content)
    except:
        return

    revs = revs_json.get('timeline', [])
    for rev in revs:
        rev = rev.get('_source', {})

        review = Review()
        review.type = "user"
        review.url = product.url

        date = rev.get('date_created')
        if date:
            review.date = date.split()[0]

        author = rev.get('author')
        author_ssid = rev.get('user_id')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=str(author_ssid)))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        is_recommended = rev.get('would_recommend_product')
        if is_recommended is True:
            review.add_property(value=True, type='is_recommended')

        is_verified = rev.get('verified_by_shop')
        if is_verified is True:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('helpful')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        title = rev.get('review_title')
        excerpt = rev.get('comments')
        if excerpt and len(remove_emoji(excerpt).replace('\r\n', '').strip()) > 2:
            if title:
                review.title = remove_emoji(title).replace('\r\n', '').strip()

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\r\n', '').strip()
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                ssid = str(rev.get('_id'))
                if ssid:
                    review.ssid = ssid.split('-')[-1]
                else:
                    review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    revs_cnt = context.get('revs_cnt', revs_json.get('stats', {}).get('review_count', 0))
    offset = context.get('offset', 0) + 100
    if offset < revs_cnt:
        next_page = context.get('page', 1) + 1
        next_url = 'https://api.reviews.io/timeline/data?type=product_review&store=bargainmax&sort=date_desc&page={page}&per_page=100&sku={sku_code}&enable_avatars=false&include_subrating_breakdown=1&must_have_comments=true&branch=&tag=&include_product_reviews=1&lang=en'.format(page=next_page, sku_code=context['sku_code'])
        session.queue(Request(next_url, use="curl", force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, offset=offset, page=next_page, revs_cnt=revs_cnt))

    elif product.reviews:
        session.emit(product)
