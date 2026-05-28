from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Varumärken', 'Nyheter']
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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://eleven.se/', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class="navigation__menu"]/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name and name not in XCAT:
            session.queue(Request(url, force_charset='utf-8'), process_category, dict(cat=name))


def process_category(data, context, session):
    strip_namespace(data)

    subcats = data.xpath('//div[@class="page-intro__sublinks"]/a')
    for subcat in subcats:
        name = subcat.xpath('div/text()').string()
        url = subcat.xpath('@href').string()

        if name and url:
            session.queue(Request(url+'?Rating=1&Rating=2&Rating=3&Rating=4&Rating=5', force_charset='utf-8'), process_prodlist, dict(cat=context['cat']+'|'+name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="product-list__list"]/div')
    if not prods:
        return

    for prod in prods:
        name = prod.xpath('@aria-label').string()
        url = prod.xpath('a/@href').string()
        ssid = prod.xpath('@data-prod-id').string()

        if ssid and ssid not in DUPE_PRODS and name and url:
            DUPE_PRODS.append(ssid)
            session.queue(Request(url, force_charset='utf-8'), process_product, dict(context, name=name, url=url, ssid=ssid))

    next_url = data.xpath('//li/a[contains(@aria-label, "next page")]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//span[@class="brand-link__text"]/text()').string()

    prod_json = data.xpath('//script[@id="__NUXT_DATA__"]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)
        for info in prod_json:
            if isinstance(info, unicode) and 'cr.testfreaks.com/reviews' in info:
                session.do(Request(info, force_charset='utf-8'), process_reviews, dict(product=product))
                break


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('reviews', [])
    for rev in revs:
        if rev.get('lang') not in ('sv', 'se') or rev.get('client_id') != 'eleven.se':
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.get('date')

        author = rev.get('author')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('score')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('verified_buyer')
        if is_verified_buyer is True:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('votes_up')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('votes_down')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        excerpt = rev.get('extract')
        if excerpt:
            excerpt = remove_emoji(excerpt.replace('\n', '').replace('\r', '')).strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    next_url = revs_json.get('next_page_url')
    if next_url:
        session.do(Request(next_url, force_charset='utf-8'), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
