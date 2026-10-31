from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Brands']
MPNS = []


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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.storedj.com.au/', force_charset='utf-8', use='curl', max_age=0), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//div[@class="mobile-menu"]/ul/li')
    for cat in cats:
        name = cat.xpath('div/a/span[@class="category"]/text()').string()

        subcats = cat.xpath('ul[@class="sub-menu"]/li/a')
        for subcat in subcats:
            subcat_name = subcat.xpath('span[@class="subcat-name"]/text()').string()
            url = subcat.xpath('@href').string()

            prods_cnt = subcat.xpath('span[@class="count"]/text()').string()
            if prods_cnt:
                prods_cnt = int(prods_cnt.strip('( )'))
                if prods_cnt > 0:
                    page_cnt = prods_cnt // 20 + 1
                    url += '?category%5BmaxPage%5D=' + str(page_cnt)
                    session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name+'|'+subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//div[@class="product-card"]')
    for prod in prods:
        name = prod.xpath('.//div[contains(@class, "title")]/p/text()').string()
        url = prod.xpath('a/@href').string()
        manufacturer = prod.xpath('.//span[@class="brand"]/text()').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, manufacturer=manufacturer, url=url))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat'].replace(' / ', '/')
    product.manufacturer = context['manufacturer']

    mpn = data.xpath('//span[@class="SKU"]/text()').string()
    if not mpn or mpn in MPNS:
        return

    MPNS.append(mpn)
    product.add_property(type='id.manufacturer', value=mpn)

    revs_url = 'https://api.trustpilot.com/v1/product-reviews/business-units/5487e55500006400057c0ed1/reviews?apikey=7qfADKhmajegupAzebRovRVAjxdpou0s&sku={}&perPage=100'.format(mpn)
    session.do(Request(revs_url, force_charset='utf-8', use='curl', max_age=0), process_reviews, dict(product=product))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    try:
        revs = simplejson.loads(data.content).get('productReviews', [])
    except:
        return

    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('id')

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('consumer', {}).get('displayName', '').strip(' +-')
        author_ssid = rev.get('consumer', {}).get('id')
        if author and author_ssid:
            author = remove_emoji(author).strip()
            review.authors.append(Person(name=author, ssid=author_ssid))
        elif author:
            author = remove_emoji(author).strip()
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('stars')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('content')
        if excerpt:
            excerpt = remove_emoji(excerpt).strip(' +-()')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)
