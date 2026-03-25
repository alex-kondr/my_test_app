from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Used', "Deals"]


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
                               u"&#\d+;"  # HTML entities
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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://harrisoncameras.co.uk/', use='curl', force_charset='utf-8', max_age=0), process_frontpage, {})


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@id="mobile-menu"]/ul/li')
    for cat in cats:
        name = cat.xpath('text()').string()

        if name not in XCAT:
            subcats = cat.xpath('.//div[contains(@class, "column") and not(h3[regexp:test(., "Brand", "i")])]/ul/li/a[not(regexp:test(., "all ", "i"))]')
            for subcat in subcats:
                subcat_name = subcat.xpath('text()').string()
                url = subcat.xpath('@href').string()

                if url and subcat_name:
                    session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name+'|'+subcat_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//ul/li[@class="grid__item"]')
    for prod in prods:
        name = prod.xpath('.//h3[contains(@class, "card__heading")]/a/text()').string()
        url = prod.xpath('.//h3[contains(@class, "card__heading")]/a/@href').string()

        revs_cnt = prod.xpath('.//span[@class="jdgm-prev-badge__text"]/text()').string()
        if revs_cnt:
            revs_cnt = revs_cnt.split()[0]
            if revs_cnt.isdigit() and int(revs_cnt) > 0:
                session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div[contains(@class, "product ")]/@data-id').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[@itemprop="brand"]/meta/@content').string()

    sku = data.xpath('//p[@class="sku"]/text()[regexp:test(., "product code:", "i")]/following-sibling::*[1][self::strong]/text()').string()
    if sku and sku.isdigit() and 3 < len(sku) < 8:
        product.sku = sku
    elif sku and len(sku) > 4:
        product.add_property(type='id.manufacturer', value=sku)

    ean = data.xpath('//p[@class="sku"]/text()[regexp:test(., "Barcode:", "i")]/following-sibling::*[1][self::strong]/text()').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    if product.ssid:
        rev_url = 'https://judge.me/reviews/reviews_for_widget?url=5c5c22-eb.myshopify.com&shop_domain=5c5c22-eb.myshopify.com&platform=shopify&page=1&per_page=10&product_id=' + product.ssid
        session.do(Request(rev_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    revs_html = data.parse_fragment(revs_json["html"])

    revs = revs_html.xpath("//div[contains(@class, 'jdgm-rev jdgm-divider-top')]")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath("@data-review-id").string()

        date = rev.xpath(".//span[contains(@class, 'timestamp')]/@data-content").string()
        if date:
            review.date = date.split()[0]

        author = rev.xpath(".//span[contains(@class, 'author') and not(regexp:test(., 'null|Anonymous', 'i'))]/text()").string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath(".//span/@data-score").string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('@data-verified-buyer').string()
        if is_verified == 'true':
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.xpath('@data-thumb-up-count').string()
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('@data-thumb-down-count').string()
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.xpath(".//b[contains(@class, 'title')]//text()").string()
        excerpt = rev.xpath(".//div[@class='jdgm-rev__body']//text()").string(multiple=True)
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

    next_url = revs_html.xpath('//a[contains(@class, "load-more")]/@data-page').string()
    if next_url:
        next_page = context.get("page", 1) + 1
        revs_url = 'https://judge.me/reviews/reviews_for_widget?url=5c5c22-eb.myshopify.com&shop_domain=5c5c22-eb.myshopify.com&platform=shopify&page=' + str(next_page) + '&per_page=10&product_id=' + product.ssid
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, page=next_page))

    elif product.reviews:
        session.emit(product)
