from agent import *
from models.products import *
import re
import simplejson


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


def is_english(content):
    en_words = "this you have or the and"
    en_words_re = re.compile("|".join(map(lambda s: r"\b%s\b" % s, en_words.split(" "))))
    return en_words_re.search(content.lower())


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://heimkinowelten.de/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('(//div[contains(@id, "porto-product-categories")])[1]//a[contains(@aria-label, "category")]')
    for cat in cats:
        name = cat.xpath('.//h3/text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_subcategory, dict(cat=name))


def process_subcategory(data, context, session):
    strip_namespace(data)

    subcats = data.xpath('//li[contains(@class, "filter-item")]/a') or data.xpath('(//div[contains(@id, "porto-product-categories")])[1]//a[contains(@aria-label, "category")]')
    for subcat in subcats:
        name = subcat.xpath('.//h3/text()').string() or subcat.xpath('text()').string()
        url = subcat.xpath('@href').string()
        if name:
            url = url + '&count=180' if '?' in url else url + '?count=180'
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="product-content"]')
    for prod in prods:
        name = prod.xpath('a[contains(@class, "product")]/h3/text()').string()
        url = prod.xpath('a[contains(@class, "product")]/@href').string()

        revs_cnt = prod.xpath('.//strong[@class="rating"]/text()').string()
        if revs_cnt and float(revs_cnt) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div/@data-product-id').string()
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[contains(@property, "brand")]/@content').string()

    mpn = ''
    prod_json = data.xpath('''//script[contains(., '"@type":"ProductGroup"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json).get('@graph', [{}])[0].get('hasVariant', [{}])[0] or simplejson.loads(prod_json).get('@graph', [{}])[0]

        mpn = prod_json.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('gtin13') or prod_json.get('gtin')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    if not mpn:
        mpn = data.xpath('//span[@class="sku"]/text()').string()
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

    revs = data.xpath('//ol/li[contains(@class, "review")]/div')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@id').string().split('-')[-1]

        date = rev.xpath('.//time/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//strong[contains(@class, "author")]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[@class="star-rating"]/@title').string()
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//p[contains(@class, "is-verified")]').string()
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.xpath('.//div[@class="description"]/p//text()').string(multiple=True)
        if excerpt and not is_english(excerpt):
            excerpt = remove_emoji(excerpt).strip()
            if len(excerpt) > 1:
                review.add_property(type="excerpt", value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
