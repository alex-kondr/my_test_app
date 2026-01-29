from agent import *
from models.products import *
import re


XCAT = ['EU-Neuwagen', 'Blog', 'Marken', 'Weber Ersatzteile']


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
    session.queue(Request('https://motorgarten.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="navigation-flyout"]/div')
    for cat in cats:
        name = cat.xpath('div[contains(@class, "flyout-bar")]//a/@title').string()

        if name and name not in XCAT:
            cats1 = cat.xpath('div[contains(@class, "content")]//div[contains(@class, "is-level-0")]/div')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a/span/text()').string()

                sub_cats = cat1.xpath('div/div/a')
                if sub_cats:
                    for sub_cat in sub_cats:
                        subcat_name = sub_cat.xpath('span/text()').string()
                        url = sub_cat.xpath('@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name, cat_url=url))

                else:
                    url = cat1.xpath('a/@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name, cat_url=url))

def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="product-info"][not(.//span[@class="no-rating"])]/a')
    for prod in prods:
        name = prod.xpath('text()').string().split(' (jetzt')[0]
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_page = data.xpath('//li[contains(@class, "page-next")][not(contains(@class, "disabled"))]/input/@value').string()
    if next_page:
        next_url = context['cat_url'] + '?p=' + next_page
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[contains(@name, "[id]")]/@value').string()
    product.category = context['cat'].replace('|Sonstiges', '')
    product.manufacturer = data.xpath('//img[contains(@class, "manufacturer")]/@title').string()

    mpn = data.xpath('//span[@class="product-detail-ordernumber"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('(//span[@itemprop="gtin13" or @itemprop="gtin12"]|//meta[@itemprop="gtin13"])/@content').string()
    if not ean:
        ean = data.xpath('//script[contains(., "productEAN")]/text()').string()
        if ean:
            ean = ean.split('"productEAN":"')[-1].split('"')[0].split(',')[0].strip()

    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs_url = 'https://motorgarten.de/product/%s/reviews' % product.ssid
    session.do(Request(revs_url), process_reviews, dict(product=product, revs_url=revs_url))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//div[@class="product-detail-review-item"]')
    for rev in revs:
        if rev.xpath('.//meta[@itemprop="inLanguage"]/@content').string() != 'de-DE':
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//div[contains(@class, "item-date")]/p/small/text()').string()
        if date:
            review.date = date.rsplit(' ', 1)[0]

        grade_overall = rev.xpath('.//p[contains(@class, "rating-alt-text")]/text()').string()
        if grade_overall:
            grade_overall = float(grade_overall.replace('Bewertung mit ', '').split()[0])
            if grade_overall > 0:
                review.grades.append(Grade(type="overall", value=grade_overall, best=5.0))

        is_verified = rev.xpath('.//div[contains(@class, "item-verify")]').string()
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.xpath('.//div[contains(@class, "item-title")]/p/text()').string()
        excerpt = rev.xpath('p[@itemprop="description"]//text()').string(multiple=True)
        if excerpt:
            if title and 'Trusted Shops' not in title:
                review.title = remove_emoji(title).strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt.replace('\n', ' ')).strip(' -,.')
            if excerpt:
                review.add_property(type="excerpt", value=excerpt)

                review.ssid = review.digest(excerpt)

                product.reviews.append(review)

    next_page = data.xpath('//li[contains(@class, "page-next")][not(contains(@class, "disabled"))]/input/@value').string()
    if next_page:
        next_url = context['revs_url'] + '?p=' + next_page
        session.do(Request(next_url), process_reviews, dict(context, product=product))

    elif product.reviews:
        session.emit(product)
