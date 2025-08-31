from agent import *
from models.products import *
import re


XCAT = ['Ankauf', 'SALE', 'Aktionen', 'Magazin', 'Workshops', 'Filialen', 'Services', 'Second Hand']


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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request("https://www.calumetphoto.de/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul/li[contains(@class, "list-item")]/a')
    for cat in cats:
        name = cat.xpath('span[@itemprop="name"]/text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_category, dict(cat=name))


def process_category(data, context, session):
    strip_namespace(data)

    subcats = data.xpath('//li[contains(@class, "swiper-slide")]/a')
    if not subcats:
        process_prodlist(data, context, session)

    for subcat in subcats:
        name = subcat.xpath('.//text()').string(multiple=True)
        url = subcat.xpath('@href').string()
        session.queue(Request(url), process_category, dict(cat=context['cat']+'|'+name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//a[contains(@class, "card")]')
    for prod in prods:
        name = prod.xpath('.//div[contains(@class, "product-name")]//text()').string()
        url = prod.xpath('@href').string()

        revs_cnt = prod.xpath('.//div[@class="product-reviews-count"]/text()').string()
        if revs_cnt and int(revs_cnt.strip('( )')) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, context)


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.sku = data.xpath('//span[@class="product-detail-ordernumber"]/text()').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//a[@class="product-detail-manufacturer-link"]/@title').string()

    mpn = data.xpath('//strong[contains(text(), "Herstellernummer (MPN):")]/following-sibling::text()[1]').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//strong[contains(text(), "EAN/GTIN:")]/following-sibling::text()[1]').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[contains(@class, "review-list-content")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//div[contains(@class, "review-item-date")]/p/text()').string()

        author = rev.xpath('p[not(@class)]/text()').string()
        if author:
            author = remove_emoji(author).strip()
            if author:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//div[@class="point-rating point-full"])')
        if grade_overall > 0:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.xpath('.//div[contains(@class, "item-title")]/p//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[contains(@class, "review-item-content")]//text()').string(multiple=True)
        if excerpt and len(remove_emoji(excerpt).strip(' +-*')) > 2:
            if title:
                review.title = remove_emoji(title).strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip(' +-*')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # Loaded all revs
