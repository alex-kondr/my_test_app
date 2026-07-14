from agent import *
from models.products import *
import re
import simplejson
import time
import random


XCAT = ['Alle anzeigen', 'Geschenkgutscheine', 'Hochbeete', 'Oster- & Frühjahrsdeko', 'Sortiment']


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
    session.queue(Request('https://www.globus-baumarkt.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    cats = data.xpath('//div[contains(@class, "dropdown-menu")]/ul/li[contains(@class, "item")]/a')
    for cat in cats:
        name = cat.xpath('@title').string()
        url = cat.xpath('@href').string()

        if name and name not in XCAT:
            session.queue(Request(url), process_category, dict(cat=name))


def process_category(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    subcats = data.xpath('//a[contains(@class, "subcategory-item")]')
    for subcat in subcats:
        name = subcat.xpath('div[contains(@class, "name")]/text()').string()
        url = subcat.xpath('@href').string().strip('+%0A ').split('+')[-1]
        if name and url:
            session.queue(Request(url), process_category, dict(cat=context['cat']+'|'+name))

    if not subcats:
        process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    prods = data.xpath('//div[@data-product-id][not(contains(@data-product-id, ".Master"))]//a')
    for prod in prods:
        name = prod.xpath('.//span[@class="product-name "]/text()').string()
        url = prod.xpath('@href').string()

        if name and url:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div[contains(@class, "product-id")]/text()').string().strip()
    product.sku = data.xpath('//*[@id-type="productNumber"]/@record-id').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[@property="product:brand"]/@content').string()

    prod_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        mpn = prod_json.get('mpn')
        if mpn and len(mpn) > 5:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('gtin13')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_cnt = data.xpath('//a[contains(@class, "reviews-link")]/text()').string()
    if revs_cnt and revs_cnt[0].isdigit():
        revs_cnt = int(revs_cnt.split()[0])
        if revs_cnt > 0:
            payload = {'p': '1'}
            url = 'https://www.globus-baumarkt.de/product/{}/reviews'.format(product.ssid)
            session.do(Request(url, method="POST", data=payload), process_reviews, dict(product=product, revs_cnt=revs_cnt))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//div[@id="review-list"]/div/div[contains(@class, "review-item")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        # no date

        author = rev.xpath('.//span[contains(@class, "review-author")]//text()').string(multiple=True)
        if author:
            author = remove_emoji(author).strip()
            if author and len(author) > 2:
                review.authors.append(Person(name=author, ssid=author))
            else:
                author = None

        grade_overall = rev.xpath('count(.//div[contains(@class, "point-full")]) + count(.//div[contains(@class, "point-partial-placeholder")]) div 2')
        if float(grade_overall) > 0:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//div[contains(@class, "review-item-verify")]//text()').string(multiple=True)
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp = rev.xpath('.//div[contains(@class, "rating-info")]/p/text()').string()
        if hlp:
            hlp_yes = hlp.split(' von ')[0].strip()
            if hlp_yes and hlp_yes.isdigit() and int(hlp_yes) > 0:
                review.add_property(type='helpful_votes', value=int(hlp_yes))

            hlp_total = hlp.split(' von ')[-1].split()[0].strip()
            if hlp_total and hlp_total.isdigit() and int(hlp_total) > 0:
                review.add_property(type='not_helpful_votes', value=int(hlp_total) - int(hlp_yes))

        title = rev.xpath('.//div[contains(@class, "title")]/h3//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[contains(@class, "review-item-content")]//text()').string(multiple=True)
        if excerpt and len(remove_emoji(excerpt).strip()) > 2:
            if title:
                review.title = remove_emoji(title).strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip()
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 10
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        payload = {'p': next_page}
        url = 'https://www.globus-baumarkt.de/product/{}/reviews'.format(product.ssid)
        session.do(Request(url, method="POST", data=payload), process_reviews, dict(context, product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
