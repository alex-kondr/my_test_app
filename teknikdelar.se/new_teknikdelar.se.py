from agent import *
from models.products import *
import simplejson
import re
import HTMLParser


h = HTMLParser.HTMLParser()


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
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.teknikdelar.se/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ul[contains(@class, "main-nav")]/li/a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()
        session.queue(Request(url + '?order=5'), process_catlist, dict(cat=name))


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    sub_cats = data.xpath('//div[contains(@class, "sub-categories")]/ul/li/a')
    if sub_cats:
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = sub_cat.xpath('@href').string()
            session.queue(Request(url + '?order=5'), process_prodlist, dict(cat=context['cat'] + '|' + sub_name))
    else:
        process_prodlist(data: Response, context: dict[str, str], session: Session)


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//a[@class="product-card"]')
    for prod in prods:
        name = prod.xpath('.//p[@class="product-name"]/text()').string()
        url = prod.xpath('@href').string()

        revs_cnt = prod.xpath('.//span[@class="score"]/text()').string()
        if revs_cnt:
            revs_cnt = int(revs_cnt.strip('( )'))
            if revs_cnt > 0:
                session.queue(Request(url), process_product, dict(context, name=name, url=url, revs_cnt=revs_cnt))
            else:
                return
        else:
            return

    next_url = data.xpath('//a[span[@class="next-link"]]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = data.xpath('//li[contains(strong, "Brand")]/text()').string(multiple=True)

    mpn = data.xpath('//tr[th[contains(., "Artnr")]]/td/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//tr[regexp:test(th, "EAN|GTIN")]/td/text()').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    try:
        prod_json = data.xpath('//script[contains(., "window.route = ")]/text()').string()
        prod_json = prod_json.replace('window.route = ', '').split('window.routes =')[0]
        fixed_json = re.sub(r'\bvoid\s+0\b', 'null', prod_json)
        fixed_json = re.sub(
            r'([{,]\s*)([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:',
            r'\1"\2":',
            fixed_json
        )
        prod_json = simplejson.loads(fixed_json).get('state', {}).get('hydration', {})
        for val in prod_json.values():
            if '"sku"' in val:
                product.ssid = simplejson.loads(val).get('data', {}).get('id')
                product.sku = product.ssid
                break
    except:
        return

    if product.ssid:
        revs_url = 'https://www.teknikdelar.se/api/products/{}/reviews?offset=0&limit=5&locale=sv&sid=1'.format(product.ssid)
        session.do(Request(revs_url), process_reviews, dict(context, product=product))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = context['product']

    revs = simplejson.loads(data.content) or []
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('id')
        review.date = rev.get('created_at')

        author = rev.get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('score')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('review')
        if excerpt:
            excerpt = remove_emoji(h.unescape(excerpt)).replace('\n', '').replace('\t', '').replace('\r', '').strip(' +-*.;•–')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        next_url = 'https://www.teknikdelar.se/api/products/{ssid}/reviews?offset={offset}&limit=5&locale=sv&sid=1'.format(ssid=product.ssid, offset=offset)
        session.do(Request(next_url), process_reviews, dict(context, product=product, offset=offset))

    elif product.reviews:
        session.emit(product)