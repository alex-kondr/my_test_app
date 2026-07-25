from agent import *
from models.products import *
import simplejson
import re
from datetime import datetime
import time
import random


XCAT = ['Angebote', 'Online Kurse']


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
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.arktis.de/', force_charset='utf-8', use='curl', max_age=0), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    cats = data.xpath('//ul[contains(@class, "list-menu--inline")]/li ')
    for cat in cats:
        name = cat.xpath('span/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('ul/li')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a/text()').string() or cat1.xpath('text()').string(multiple=True)

                subcats = cat1.xpath('ul/li/a')
                if subcats:
                    for subcat in subcats:
                        subcat_name = subcat.xpath('text()').string()
                        session.queue(Request(url, force_charset='utf-8', use='curl', max_age=0), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                else:
                    url = cat1.xpath('a/@href').string()
                    session.queue(Request(url, force_charset='utf-8', use='curl', max_age=0), process_prodlist, dict(cat=name+'|'+cat1_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    prods = data.xpath('//h3[contains(@class, "card-information")]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string().split('?')[0]
        session.queue(Request(url, force_charset='utf-8', use='curl', max_age=0), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8', use='curl', max_age=0), process_prodlist, context)


def process_product(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="product-id"]/@value').string()
    product.category = context['cat']

    sku = data.xpath('//div[@id="custom-sku"]/text()').string()
    if sku:
        product.sku = sku.split(': ')[-1].strip()

    prod_json = data.xpath('''//script[contains(., '"@type": "Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')

    ean = data.xpath('''//script[contains(., '"barcode":"')]/text()''').string()
    if ean:
        ean = ean.split('"barcode":"')[-1].split('"', 1)[0]
        product.add_property(type='id.ean', value=ean)

    revs_cnt = data.xpath('//div/@data-raters').string()
    if revs_cnt and revs_cnt.isdigit():
        revs_cnt = int(revs_cnt)
        if revs_cnt > 0:
            revs_url = 'https://loox.io/widget/BHZP4E4jXM/reviews/{ssid}?language=de'.format(ssid=product.ssid)
            session.do(Request(revs_url, force_charset='utf-8', use='curl', max_age=0), process_reviews, dict(product=product, revs_cnt=revs_cnt))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    product = context["product"]

    revs = data.xpath('//div[@id="grid"]//div[@class="box"]')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url

        date = rev.xpath('div/@data-time').string()
        if date:
            review.date = datetime.fromtimestamp(int(date) / 1000).strftime("%d.%m.%Y")

        author = rev.xpath('div[contains(@class, "title")]/text()').string()
        if author and 'anonym' not in author.lower():
            review.authors.append(Person(name=author, ssid=author))
        else:
            author = None

        grade_overall = rev.xpath('count(.//svg[@data-lx-fill="full"])')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//span[contains(text(), "Verifiziert")]')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.xpath('.//div[contains(@class, "main-text")]//text()').string(multiple=True)
        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\r', '').replace('\n', '').strip()
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                ssid = rev.xpath('div/@data-testid').string()
                if ssid:
                    review.ssid = ssid.replace('review-', '').replace('-title', '').strip('- ')
                else:
                    review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 20
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        revs_url = 'https://loox.io/widget/BHZP4E4jXM/reviews/{ssid}?language=de&page={page}'.format(ssid=product.ssid, page=next_page)
        session.do(Request(revs_url, force_charset='utf-8', use='curl', max_age=0), process_reviews, dict(context, product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
