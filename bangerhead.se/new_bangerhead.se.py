from agent import *
from models.products import *
import re


XCAT = ['Varumärken', 'Kampanjer', 'Support']


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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.bangerhead.se/', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//nav[@class="menu-list"]/div[contains(@class, "menu-item")]/label')
    for cat in cats:
        name = cat.xpath('span/text()').string()
        cat1_id = cat.xpath('@for').string()

        if name not in XCAT and cat1_id:
            cat1_id = cat1_id.replace('sub-', '')
            cats1 = data.xpath('//div[@id="{id}-panel"]/div[contains(@class, "sub-menu")]|//div[@id="{id}-panel"]/a[contains(@class, "sub-menu")]'.format(id=cat1_id))
            for cat1 in cats1:
                cat1_name = cat1.xpath('.//text()').string(multiple=True)
                subcats_id = cat1.xpath('label/@for').string()

                if 'Allt inom ' not in cat1_name:
                    if subcats_id:
                        subcats_id = subcats_id.replace('sub-', '')
                        subcats = data.xpath('//div[@id="{}-panel"]/a'.format(subcats_id))
                        for subcat in subcats:
                            subcat_name = subcat.xpath('text()').string()
                            url = subcat.xpath('@href').string()

                            if  'Allt inom ' not in subcat_name:
                                session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                    else:
                        url = cat1.xpath('@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//a[contains(@class, "card__name")]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//a[contains(@class, "product-summary__brand")]/text()').string()

    prod_info = data.xpath('''//script[contains(., '"gtin13":')]/text()''').string()
    if prod_info:
        ean = prod_info.split('"gtin13": "', 1)[-1].split('", "')[0].strip()
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//ul[contains(@class, "review-list")]/li')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//span[contains(@class, "review-date")]/text()').string( )

        author = rev.xpath('p[contains(@class, "review-author")]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//span[contains(@class, "review-star--active")])')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('p[contains(@class, "review-content")]//text()').string(multiple=True)
        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\t', '').replace('\n', ' ').replace('  ', ' ').strip(' +-*.')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
