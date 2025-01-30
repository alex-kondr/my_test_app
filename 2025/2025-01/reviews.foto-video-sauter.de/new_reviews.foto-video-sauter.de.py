from agent import *
from models.products import *
import re


XCAT = ['SALE', 'Aktionen', 'Second Hand', 'Ankauf', 'Workshops', 'Services']


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
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.foto-video-sauter.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//a[contains(@class, "nav-link main-navigation-link")]')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_category, dict(cat=name))


def process_category(data, context, session):
    sub_cats = data.xpath('//a[contains(@class, "inpage-navigation__category")]')
    for sub_cat in sub_cats:
        name = sub_cat.xpath('div[@class="inpage-navigation__title"]//text()').string(multiple=True)
        url = sub_cat.xpath('@href').string()
        session.queue(Request(url), process_category, dict(cat=context['cat'] + '|' + name))

    if not sub_cats:
        process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "card product-box")]')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('.//a[@class="product-name"]/text()').string()
        product.url = prod.xpath('.//a[@class="product-name"]/@href').string()
        product.ssid = prod.xpath('.//input[@name="product-id"]/@value').string()
        product.sku = prod.xpath('.//meta[@itemprop="sku"]/@content').string()
        product.category = context['cat']
        product.manufacturer = prod.xpath('.//meta[@itemprop="name"]/@content').string()

        mpn = prod.xpath('.//meta[@itemprop="mpn"]/@content').string()
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod.xpath('.//meta[@itemprop="gtin13"]/@content').string()
        if ean:
            product.add_property(type='id.ean', value=ean)

        revs = prod.xpath('.//calumet-icon[@symbol="star-full" or @symbol="star-half"]')
        if revs:
            session.do(Request(product.url), process_product, dict(product=product))


def process_product(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="row review-item"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//div[contains(@class, "date")]//text()').string(multiple=True)

        author = rev.xpath('.//div[contains(@class, "content")]/p[not(@class)]//text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//calumet-icon[@symbol="star-full"]) + count(.//calumet-icon[@symbol="star-half"]) div 2')
        if grade_overall and grade_overall > 0:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.xpath('.//p[@class="h5"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[contains(@class, "content")]//text()').string(multiple=True)
        if excerpt and title:
            review.title = remove_emoji(title).strip(' +-.\n\t')
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip(' +-.\n\t')
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page