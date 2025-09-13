from agent import *
from models.products import *
import simplejson
import re
import HTMLParser


h = HTMLParser.HTMLParser()

XCAT = ['Our Services', 'Sales & Deals', 'Fun Reads']


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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.worldwidestereo.com/', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats1 = data.xpath('//li[@class="menu-drawer__parent"]')
    for cat1 in cats1:
        name1 = cat1.xpath('details/summary/span[contains(@class, "item-title")]/text()').string()
        if name1:
            cats2 = cat1.xpath('.//ul[contains(@class, "menu--second-level")]/li/details')
            for cat2 in cats2:
                name2 = cat2.xpath('summary/span[contains(@class, "item-title")]/text()').string()

                cats3 = cat2.xpath('.//li[regexp:test(., "shop by category", "i")]/following-sibling::ul[1]/li/a')
                if not cats3:
                    cats3 = cat2.xpath('.//div[contains(@class, "submenu__row-linklist")][li[regexp:test(., "by type", "i")]]//a')
                if not cats3:
                    cat_id = cat2.xpath('.//a[contains(@class, "view-all")]/@href').string().split('/')[-1]
                    cat_url = 'https://5949mp.a.searchspring.io/api/search/search.json?&domain=https%3A%2F%2Fwww.worldwidestereo.com%2Fcollections%2F{}&siteId=5949mp&resultsPerPage=24&resultsFormat=native'.format(cat_id)
                    session.queue(Request(cat_url, max_age=0), process_prodlist, dict(cat=name1+'|'+name2, cat_url=cat_url))

                for cat3 in cats3:
                    name3 = cat3.xpath('span/text()').string()
                    cat_id = cat3.xpath('@href').string().split('/')[-1]
                    cat_url = 'https://5949mp.a.searchspring.io/api/search/search.json?&domain=https%3A%2F%2Fwww.worldwidestereo.com%2Fcollections%2F{}&siteId=5949mp&resultsPerPage=24&resultsFormat=native'.format(cat_id)
                    session.queue(Request(cat_url, max_age=0), process_prodlist, dict(cat=name1+'|'+name2+'|'+name3, cat_url=cat_url))


def process_prodlist(data, context, session):
    prods_json = simplejson.loads(data.content)

    prods = prods_json.get('results')
    for prod in prods:
        name = prod.get('name')
        brand = prod.get('brand')
        url = 'https://www.worldwidestereo.com' + prod.get('url')
        sku = str(prod.get('sku'))

        revs_cnt = prod.get('ratingCount')
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url, max_age=0), process_product, dict(context, name=name, url=url, brand=brand, sku=sku))

    prods_cnt = prods_json.get('pagination', {}).get('totalResults')
    if prods_cnt:
        offset = context.get('offset', 0) + 24
        if offset < prods_cnt:
            next_page = context.get("page", 1) + 1
            next_url = context['cat_url'] + '&page=' + str(next_page)
            session.queue(Request(next_url, max_age=0), process_prodlist, dict(context, page=next_page, offset=offset))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = h.unescape(context["name"])
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="product-id"]/@value').string()
    product.sku = context["sku"]
    product.category = context['cat']
    product.manufacturer = h.unescape(context['brand'])

    mpn = data.xpath('//span[@class="variant-model"]/text()').string()
    if mpn:
        mpn = mpn.split()[-1]
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//span[@class="variant-barcode"]/text()').string()
    if ean:
        ean = ean.split()[-1]
        product.add_property(type='id.ean', value=ean)

    revs_url = 'https://fast.a.klaviyo.com/reviews/api/client_reviews/{}/?company_id=HPkiQj&limit=5&offset=0&sort=3&type=reviews'.format(product.ssid)
    session.do(Request(revs_url, max_age=0, force_charset='utf-8'), process_reviews, dict(context, product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev['id'])

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('author')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.get('verified')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('title')
        excerpt = rev.get('content')
        if excerpt and remove_emoji(excerpt).strip() > 2:
            if title:
                review.title = remove_emoji(title).strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(h.unescape(excerpt)).replace('<br />', '').replace('\n', '').strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = revs_json.get('filtered_count', 0)
    offset = context.get('offset', 0) + 5
    if offset < revs_cnt:
        revs_url = 'https://fast.a.klaviyo.com/reviews/api/client_reviews/{ssid}/?company_id=HPkiQj&limit=5&offset={offset}&sort=3&type=reviews'.format(ssid=product.ssid, offset=offset)
        session.do(Request(revs_url, max_age=0, force_charset='utf-8'), process_reviews, dict(product=product, offset=offset))

    elif product.reviews:
        session.emit(product)
