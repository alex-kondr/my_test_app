from agent import *
from models.products import *
import re


XCAT = ['Behandlungen ', 'Beratung ', 'Hautberatungsteam', 'Werte', 'Magazin']


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
    session.queue(Request('https://www.drhauschka.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@id="main_nav"]/ul/li')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        if name not in XCAT:
            cats1 = cat.xpath('.//div[contains(div/span/text(), "Nach Produkt")]/div[contains(@class, "level-1")]/div')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a[contains(@class, "level-1")]//text()').string(multiple=True)

                subcats = cat1.xpath('div/div/a')
                if subcats:
                    for subcat in subcats:
                        subcat_name = subcat.xpath('.//text()').string(multiple=True)
                        url = subcat.xpath('@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name, prods_url=url))
                else:
                    url = cat1.xpath('a/@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name, prods_url=url))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="product-info"]')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('a/text()').string()
        product.url = prod.xpath('a/@href').string()
        product.ssid = prod.xpath('div/@data-product-id|.//input[contains(@name, "[id]")]/@value').string()
        product.sku = prod.xpath('.//input[@name="sku"]/@value').string()
        product.category = context['cat']
        product.manufacturer = 'Dr.Hauschka'

        revs_cnt = prod.xpath('.//span[contains(@class, "rating-count")]/text()').string()
        if revs_cnt and int(revs_cnt.strip('( )')) > 0:
            revs_cnt = revs_cnt.strip('( )')
            if int(revs_cnt) > 0:
                session.queue(Request(product.url), process_product, dict(product=product, revs_cnt=int(revs_cnt)))

    prods_cnt = context.get('prods_cnt', data.xpath('//span[contains(@class, "product-count")]/text()').string())
    offset = context.get('offset', 0) + 18
    if prods_cnt and offset < int(prods_cnt):
        next_page = context.get('page', 1) + 1
        next_url = context['prods_url'] + '?p=' + str(next_page)
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = context['product']

    if not product.ssid:
        product.ssid = data.xpath('//input[@name="productId"]/@value').string()

    if not product.ssid:
        ssid = data.xpath('//div/@aria-labelledby[contains(., "review-tab-")]').string()
        if ssid:
            product.ssid = ssid.replace('review-tab-', '')

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs_url = 'https://www.drhauschka.de/product/{}/reviews'.format(product.ssid)
    session.do(Request(revs_url), process_reviews, dict(context, product=product))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        if rev.xpath('.//meta[@itemprop="inLanguage"]/@content').string() != 'de-DE':
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('.//div/@data-review-id').string()
        review.date = rev.xpath('.//p[contains(@class, "product-review-time")]/text()').string()

        author = rev.xpath('.//div[@itemprop="author"]/meta/@content').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//p[contains(@class, "product-review-rating-alt-text")]/text()').string()
        if grade_overall:
            grade_overall = grade_overall.split(' von ')[0].strip().rsplit(' ', 1)[-1]
            if grade_overall and float(grade_overall) > 0:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.xpath('.//p[contains(text(), "Verifizierter Kauf")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.xpath('.//p[contains(@class, "helpfulness-count")]/text()').string()
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        title = rev.xpath('.//h4[contains(@class, "review-headline")]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[@itemprop="description"]//text()').string(multiple=True)
        if excerpt and len(remove_emoji(excerpt).strip()) > 2:
            if title:
                review.title = remove_emoji(title)
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 10
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        revs_url = 'https://www.drhauschka.de/product/{ssid}/reviews?p={page}'.format(ssid=product.ssid, page=next_page)
        session.do(Request(revs_url), process_reviews, dict(context, product=product, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
