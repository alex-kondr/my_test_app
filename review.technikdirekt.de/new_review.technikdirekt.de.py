from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Jura Markenwelt', 'Smeg Markenwelt', 'Bosch Markenwelt', 'Neuheiten', 'Lagerräumung', 'Cashback-Aktionen', 'Gutscheine']


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
    session.queue(Request('https://www.technikdirekt.de/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//div[@class="nav-main"]/div/a')
    for cat in cats:
        name = cat.xpath('@title').string(multiple=True)

        if name not in XCAT:
            cats1 = cat.xpath('(following-sibling::*)[2][contains(@class, "navigation")]//div[contains(@class, "is-level-0")]/div')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a//text()').string(multiple=True)

                if cat1_name not in XCAT:
                    subcats = cat1.xpath('div[contains(@class, "is-level-1")]/div/a')
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.xpath('.//text()').string(multiple=True)
                            url = subcat.xpath('@href').string()
                            session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                    else:
                        url = cat1.xpath('a/@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//article[contains(@class, "product")]/header')
    for prod in prods:
        name = prod.xpath('h4/a/text()').string()
        url = prod.xpath('h4/a/@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    prods_cnt = context.get('prods_cnt', data.xpath('//p[@class="displayProducts__number"]/small/strong/text()').string())
    offset = context.get('offset', 0) + 50
    if prods_cnt and int(prods_cnt) > offset:
        next_page = context.get('page', 1) + 1
        next_url = context['cat_url'] + '&pageNumber=' + str(next_page)
        session.queue(Request(next_url), process_prodlist, dict(context, prods_cnt=prods_cnt, offset=offset, page=next_page))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs_cnt = data.xpath('//span[@class="reviews__counter"]/text()').string(multiple=True)
    if not revs_cnt or int(revs_cnt.strip('( )')) < 1:
        return

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat'].replace('Sonstiges|', '')
    product.ssid = data.xpath('//p/small[contains(@class, "orderNumber")]/strong/text()').string()
    product.sku = product.ssid

    prod_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')

        ean = prod_json.get('gtin13')
        if ean:
            product.properties.append(ProductProperty(type='id.ean', value=str(ean)))

        mpn = prod_json.get('mpn')
        if mpn and len(mpn) > 5:
            product.properties.append(ProductProperty(type='id.manufacturer', value=mpn))

    revs_url = 'https://review.technikdirekt.de/api/review/product/{}?shopIdentifier=40_-3&pageSize=10'.format(product.ssid)
    session.do(Request(revs_url), process_reviews, dict(product=product, revs_url=revs_url))

    if product.reviews:
        session.emit(product)


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    resp = simplejson.loads(data.content)

    revs = resp.get('productReviews', [])
    for rev in revs:
        if str(rev.get('productId')) != product.ssid:
            continue

        review = Review()
        review.url = product.url
        review.ssid = str(rev['reviewId'])
        review.type = 'user'

        date = rev.get('formatedDate')
        if date:
            review.date = date.split()[0]

        author = rev.get('customer')
        if author:
            author_name = remove_emoji(author.get('customerName') or 'Anonym').replace('\n', ' ').strip()
            author_ssid = author.get('customerId')
            author_email = author.get('email')
            if author_ssid and author_email:
                review.authors.append(Person(name=author_name, ssid=str(author_ssid), email=author_email))
            elif author_ssid:
                review.authors.append(Person(name=author_name, ssid=str(author_ssid)))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.get('title', '')
        excerpt = rev.get('review')
        if excerpt:
            review.title = remove_emoji(title.replace('\n', ' ')).strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt.replace('\n', ' ')).strip()

            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))

            product.reviews.append(review)

    revs_cnt = resp.get('count', 0)
    offset = context.get('offset', 0) + 10
    if revs_cnt > offset:
        next_page = context.get('page', 1) + 1
        revs_url = context['revs_url'] + '&pageNumber=' + str(next_page)
        session.do(Request(revs_url), process_reviews, dict(context, offset=offset, page=next_page))