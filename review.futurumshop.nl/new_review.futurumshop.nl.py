from agent import *
from models.products import *
import re
import HTMLParser
import simplejson


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
    session.queue(Request('https://www.futurumshop.nl/fietskleding-heren'), process_category, dict(cat='Fietskleding Heren'))
    session.queue(Request('https://www.futurumshop.nl/fietsonderdelen'), process_category, dict(cat='Fietsonderdelen'))
    session.queue(Request('https://www.futurumshop.nl/fietsen/mountainbikes'), process_category, dict(cat='Fietsen/Mountainbike'))
    session.queue(Request('https://www.futurumshop.nl/sport-elektronica'), process_category, dict(cat='Sport Elektronica'))
    session.queue(Request('https://www.futurumshop.nl/triathlon'), process_category, dict(cat='Triathlon'))


def process_category(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    subcats = data.xpath('//div[contains(@class, "backdrop-blur")]/a[contains(@class, "items-center")]')
    if not subcats:
        subcats = data.xpath('//div[contains(a/img/@alt, "Alle")]/a|//div[h3]/ul/li/a')
    if not subcats:
        process_prodlist(data: Response, context: dict[str, str], session: Session)
        return

    for subcat in subcats:
        subcat_name = subcat.xpath('.//text()').string(multiple=True)
        url = subcat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=context['cat']+'|'+subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[a/h3]')
    for prod in prods:
        name = prod.xpath('a/h3/text()').string(multiple=True).strip()
        url = prod.xpath('a/@href').string()

        revs_cnt = prod.xpath('.//span[regexp:test(normalize-space(text()), "^\(\d+\)$")]/text()').string()
        if revs_cnt:
            revs_cnt = int(revs_cnt.strip('( )'))
            if revs_cnt > 0:
                session.queue(Request(url), process_product, dict(context, name=name, url=url, revs_cnt=revs_cnt))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div/@data-product-id').string()
    product.sku = product.ssid
    product.category = context['cat']

    prod_json = data.xpath('''//script[contains(., '"@type": "Product"')]/text()''').string()
    try:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')

        ean = prod_json.get('gtin')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)
    except:
        pass

    if product.url not in DUPE_PRODS:
        DUPE_PRODS.append(product.url)

        prod_variants = data.xpath('//ul[@class="options"]/li/a/@href').strings()
        if prod_variants and len(prod_variants) > 0:
            DUPE_PRODS.extend(prod_variants)

        revs_url = 'https://www.futurumshop.nl/products/%s/reviews?page=1' % product.ssid
        session.do(Request(revs_url), process_reviews, dict(context, product=product))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    revs = data.xpath('//div[@class="productReviewsSingle"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//span[@class="date"]/text()').string()

        author = rev.xpath('.//span[@class="author"]/text()').string()
        if author:
            author = h.unescape(remove_emoji(author)).strip(' .,')
            if author:
                review.authors.append(Person(name=author, ssid=author))

        pros = rev.xpath('.//ul[@class="pros"]/li/div[@class="text"]/text()').strings()
        for pro in pros:
            pro = h.unescape(remove_emoji(pro)).strip(' ,.+-')
            review.add_property(type='pros', value=pro)

        cons = rev.xpath('.//ul[@class="cons"]/li/div[@class="text"]/text()').strings()
        for con in cons:
            con = h.unescape(remove_emoji(con)).strip(' ,.+-')
            review.add_property(type='cons', value=con)

        grade_overall = rev.xpath('.//ul[@class="js_review-rating"]/@data-score').string()
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        title = rev.xpath('.//strong[@class="title"]/text()').string()
        excerpt = rev.xpath('.//div[contains(@class, "description")]//text()').string(multiple=True)
        if excerpt and len(h.unescape(remove_emoji(excerpt)).strip(' ,').lstrip('.')) > 2:
            if title:
                review.title = h.unescape(remove_emoji(title)).strip(' .,')
        else:
            excerpt = title

        if excerpt:
            excerpt = h.unescape(remove_emoji(excerpt)).strip(' ,').lstrip('.')
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    revs_cnt = context['revs_cnt']
    offset = context.get('offset', 0) + 5
    if offset < int(revs_cnt):
        next_page = context.get('page', 1) + 1
        revs_url = 'https://www.futurumshop.nl/products/%s/reviews?page=%s' % (product.ssid, next_page)
        session.do(Request(revs_url), process_reviews, dict(context, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
