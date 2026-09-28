from agent import *
from models.products import *
import re
import HTMLParser


h = HTMLParser.HTMLParser()

DUPE_PRODS = []


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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]

    urls = [
        'https://www.futurumshop.nl/fietskleding-heren',
        'https://www.futurumshop.nl/fietskleding-dames',
        'https://www.futurumshop.nl/fietsonderdelen',
        'https://www.futurumshop.nl/fietsen',
        # 'https://www.futurumshop.nl/fiets&kamperen', — Error 404
        'https://www.futurumshop.nl/sport-elektronica',
        'https://www.futurumshop.nl/triathlon', # Wrong URLs of subcats
        'https://www.futurumshop.nl/hardlopen'  # Wrong URLs of subcats
    ]

    for url in urls:
        session.queue(Request(url), process_category, dict())


def process_category(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//div[contains(@class, "subNavigation")]') or data.xpath('//ul/li[contains(@class, "toggleGroup")]') or data.xpath('//div[@class="contentContainer"]//div[contains(@class, "banner-row center")]/a')
    if not cats:
        process_prodlist(data: Response, context: dict[str, str], session: Session)
        return

    for cat in cats:
        name = cat.xpath('div[@class="title"]/text()').string() or cat.xpath('div/h2/text()').string() or cat.xpath('.//p/span/text()').string()
        cats1 = cat.xpath('span//ul/li/a') or cat.xpath('ul[@class="js_category-list"]/li/a')
        if not cats1:
            url = cat.xpath('@href').string() + '?itemsPerPage=100'
            session.queue(Request(url), process_category, dict(cat=context.get('cat', '')+'|'+name, cat_url=url))

        for cat1 in cats1:
            name1 = cat1.xpath('text()').string()
            url = cat1.xpath('@href').string() + '?itemsPerPage=100'
            if 'images.' not in url:
                session.queue(Request(url), process_category, dict(cat=name+'|'+name1, cat_url=url))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "js_product-card")]')
    for prod in prods:
        name = prod.xpath('.//h3[contains(@class, "productTitle")]/span/text()').string(multiple=True).strip()
        url = prod.xpath('.//div[@class="text"]/a/@href').string()

        revs_cnt = prod.xpath('.//div[@class="productRating"]/span/text()').string()
        if revs_cnt:
            revs_cnt = int(revs_cnt.strip('( )'))
            if revs_cnt > 0:
                session.queue(Request(url), process_product, dict(context, name=name, url=url, revs_cnt=revs_cnt))

    last_page = context.get('last_page', data.xpath('//ol[contains(@class, "paging")]/li[last()]/@data-page').string())
    next_page = context.get('page', 1) + 1
    if last_page and next_page <= int(last_page):
        next_url = context['cat_url'] + "&page=" + str(next_page)
        session.queue(Request(next_url), process_prodlist, dict(context, page=next_page, last_page=last_page))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat'].strip('|')
    product.manufacturer = data.xpath('//span[@class="brand"]/text()').string()
    product.ssid = data.xpath('//span[@class="js_product-id"]/text()').string()
    product.sku = product.ssid

    if product.url not in DUPE_PRODS:
        revs_cnt = context['revs_cnt']
        revs_url = 'https://www.futurumshop.nl/products/%s/reviews?page=1' % product.ssid
        session.do(Request(revs_url), process_reviews, dict(product=product, revs_cnt=revs_cnt))

    if product.reviews:
        session.emit(product)

        DUPE_PRODS.append(product.url)

        prod_variants = data.xpath('//ul[@class="options"]/li/a/@href').strings()
        if prod_variants and len(prod_variants) > 0:
            DUPE_PRODS.extend(prod_variants)


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    revs = data.xpath('//div[@class="productReviewsSingle"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//span[@class="date"]/text()').string()

        title = rev.xpath('.//strong[@class="title"]/text()').string()
        if title:
            review.title = h.unescape(remove_emoji(title)).strip(' .,')

        author = rev.xpath('.//span[@class="author"]/text()').string()
        if author:
            author = h.unescape(remove_emoji(author)).strip(' .,')
            if author:
                review.authors.append(Person(name=author, ssid=author))

        pros = rev.xpath('.//ul[@class="pros"]/li/div[@class="text"]/text()').strings()
        for pro in pros:
            pro = h.unescape(remove_emoji(pro)).strip(' ,.+-')
            review.properties.append(ReviewProperty(type='pros', value=pro))

        cons = rev.xpath('.//ul[@class="cons"]/li/div[@class="text"]/text()').strings()
        for con in cons:
            con = h.unescape(remove_emoji(con)).strip(' ,.+-')
            review.properties.append(ReviewProperty(type='cons', value=con))

        grade_overall = rev.xpath('.//ul[@class="js_review-rating"]/@data-score').string()
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//div[contains(@class, "description")]//text()').string(multiple=True)
        if excerpt:
            excerpt = h.unescape(remove_emoji(excerpt)).strip(' ,').lstrip('.')
            if excerpt:
                review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    revs_cnt = context['revs_cnt']
    offset = context.get('offset', 0) + 5
    if offset < int(revs_cnt):
        next_page = context.get('page', 1) + 1
        revs_url = 'https://www.futurumshop.nl/products/%s/reviews?page=%s' % (product.ssid, next_page)
        session.do(Request(revs_url), process_reviews, dict(context, offset=offset, page=next_page))