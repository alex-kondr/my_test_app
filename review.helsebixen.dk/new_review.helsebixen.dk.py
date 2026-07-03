from agent import *
from models.products import *
import re


XCAT = ['Brands', 'Se alt', 'Gå til hovedmenu']


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
    session.queue(Request('https://www.helsebixen.dk/shop/widgets/menu/offcanvas'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[contains(@class, "navigation")]/li/a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@data-href').string()

        if name and name not in XCAT and url:
            session.queue(Request('https://www.helsebixen.dk'+url), process_catlist, dict(cat=context.get('cat', '')+'|'+name))
        elif name and name not in XCAT:
            url = cat.xpath('@href').string()
            session.queue(Request(url+'?order=anmeldelser'), process_prodlist, dict(cat=context.get('cat', '')+'|'+name, cat_url=url))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "card-body p-0")]')
    for prod in prods:
        name = prod.xpath('.//a[contains(@class, "product-name")]/text()').string()
        url = prod.xpath('.//a[contains(@class, "product-name")]/@href').string()

        rating = prod.xpath('.//div[@class="product-review-point"]')
        if rating:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))
        elif name:
            return

    next_page = data.xpath('//input[@id="p-next" and not(@disabled)]/@value').string()
    if next_page:
        next_url = context['cat_url'] + '&p=' + next_page
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//meta[@itemprop="productID"]/@content').string()
    product.sku = data.xpath('//span[@itemprop="sku"]/text()').string(multiple=True)
    product.category = context['cat'].replace(' / ', '/').strip('|')
    product.manufacturer = data.xpath('//a[contains(@class, "product-detail-manufacturer-link")]/@title').string()

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    payload = {'p': '1'}
    revs_url = 'https://www.helsebixen.dk/shop/product/{}/reviews'.format(product.ssid)
    session.do(Request(revs_url, method='POST', data=payload), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        if rev.xpath('.//meta[@itemprop="inLanguage"]/@content').string() != 'da-DK':
            continue

        review = Review()
        review.type = 'user'
        review.url = data.response_url

        date = rev.xpath('.//meta[@itemprop="datePublished"]/@content').string()
        if date:
            review.date = date.rsplit(' ', 1)[0]

        author = rev.xpath('.//div[@itemprop="author"]/meta[@itemprop="name"]/@content').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//div[contains(@class, "point-full")])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        is_verified_buyer = rev.xpath('.//small[contains(., "Verificeret køb")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.xpath('.//div[contains(@class, "review-item-title")]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[@itemprop="description"]//text()').string(multiple=True)
        if excerpt:
            if title:
                review.title = remove_emoji(title).strip(' +-')
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip(' +-')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    next_page = data.xpath('//input[@id="p-next" and not(@disabled)]/@value').string()
    if next_page:
        payload = {'p': next_page}
        revs_url = 'https://www.helsebixen.dk/shop/product/{}/reviews'.format(product.ssid)
        session.do(Request(revs_url, method='POST', data=payload), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)

