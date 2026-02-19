from agent import *
from models.products import *
import HTMLParser
import re


h = HTMLParser.HTMLParser()
XCAT = ['SALE', 'Camping-Welten', 'Unsere Marken']


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
                               u"&#\d+;"  # HTML entities
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.camping-kaufhaus.com/widgets/menu/offcanvas?navigationId=0199ecdbb9af73138656afcb301073e7', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[contains(@class, "navigation")]/li/a')
    for cat in cats:
        name = cat.xpath('span/text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, force_charset='utf-8'), process_category, dict(cat=name))


def process_category(data, context, session):
    strip_namespace(data)

    subcats = data.xpath('//li/a[contains(@class, "subcategory-navigation-link")]')
    # if not subcats:
    #     context['cat_url'] = data.response_url
    #     process_prodlist(data, context, session)
    #     return

    for subcat in subcats:
        name = subcat.xpath('.//span[contains(@class, "subcategory")]/text()').string()
        url = subcat.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_prodlist, dict(cat=context['cat']+'|'+name, cat_url=url))
        # session.queue(Request(url, force_charset='utf-8'), process_category, dict(cat=context['cat']+'|'+name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//a[@class="product-name"]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string().split('?')[0]
        session.queue(Request(url, force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_page = data.xpath('//input[@id="p-next-bottom"]/@value').string()
    if next_page:
        next_url = context['cat_url'] + '?p=' + next_page
        session.queue(Request(next_url, force_charset='utf-8'), process_prodlist, context)


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//meta[@itemprop="productID"]/@content').string()
    product.sku = data.xpath('//span[@itemprop="sku"]/text()').string()
    product.category = context['cat'].replace('Sonstiges Zubehör', '').strip()
    product.manufacturer = data.xpath('//img[@class="product-detail-manufacturer-logo"]/@alt').string()

    mpn = data.xpath('//tr[th[contains(., "Herstellernummer")]]/td//text()').string(multiple=True)
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        if rev.xpath('//meta[@itemprop="inLanguage"]/@content').string() != 'de-DE':
            continue

        review = Review()
        review.type = "user"
        review.url = product.url

        date = rev.xpath('.//meta[@itemprop="datePublished"]/@content').string()
        if date:
            review.date = date.rsplit(' ', 1)[0]

        author = rev.xpath('.//div[@itemprop="author"]/meta/@content').string()
        if author:
            author = h.unescape(remove_emoji(author)).replace(u'Ã\\x9F', u'ß').replace(u'Ã\\x9C', u'Ü').replace(u'\xe2\x80\x9c', u'"').replace(u'\xc3\x9c', u'Ü').replace(u'\xc3\x9f', u'ß').replace(u'Ã\x96', u'Ö').replace(u'Ã¼', u'ü').replace(u'\xc3\x96', u'Ö').replace(u'\xc3\xbc', u'ü').strip(' +*,')
            if author:
                review.authors.append(Person(name=author, ssid=author))
            else:
                author = None

        grade_overall = rev.xpath('.//p[contains(@class, "product-review-rating-alt-text")]/text()').string()
        if grade_overall:
            grade_overall = grade_overall.replace('Bewertung mit ', '').split()[0]
            if grade_overall and float(grade_overall) > 0:
                review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        title = rev.xpath('.//p[@class="h5"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[@itemprop="description"]//text()').string(multiple=True)
        if excerpt and h.unescape(remove_emoji(excerpt).replace('\r', '').replace('\n', ' ')).strip(' +*,').lstrip('.'):
            if title:
                review.title = h.unescape(remove_emoji(title)).replace('\r', '').replace('\n', ' ').strip(' .+*,')
        else:
            excerpt = title

        if excerpt:
            excerpt = h.unescape(remove_emoji(excerpt).replace('\r', '').replace('\n', ' ')).strip(' +*,').lstrip('.')
            if excerpt:
                review.add_property(type="excerpt", value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
