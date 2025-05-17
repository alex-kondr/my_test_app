from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Kampanjer', 'Gavekort', 'Gjenbruksbutikken', 'Outlet', 'Vis alle']

# Prune gets stuck on these pages and doesn't continue parsing
XPROD = [
    'https://www.multicom.no/pc-produksjon-stromkabel-fra-feks-vegguttak/cat-p/c100874/p10508324'
]


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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.multicom.no/', use='curl', force_charset='utf-8'), process_frontpage, {})


def process_frontpage(data, context, session):
    cats1 = data.xpath('//ul[contains(@class, "submenu-0")]/li')
    for cat1 in cats1:
        name1 = cat1.xpath('a/span[@class="elipsis"]/text()').string()

        if name1 not in XCAT:
            cats2 = cat1.xpath('ul/li[contains(@class, "submenu-1")]')
            for cat2 in cats2:
                name2 = cat2.xpath('a/span[@class="elipsis"]/text()').string()

                if name2 not in XCAT:
                    cats3 = cat2.xpath('ul/li[contains(@class, "submenu-2")]')

                    if cats3:
                        for cat3 in cats3:
                            name3 = cat3.xpath('a/span[@class="elipsis"]/text()').string()

                            if name3 not in XCAT:
                                cats4 = cat3.xpath('ul/li[contains(@class, "submenu-3")]')

                                if cats4:
                                    for cat4 in cats4:
                                        name4 = cat4.xpath('a/span[@class="elipsis"]/text()').string()
                                        if name4 and name4 not in XCAT:
                                            url = cat4.xpath('a/@href').string()
                                            session.queue(Request(url, use='curl', force_charset='utf-8'), process_category, dict(cat=name1+'|'+name2+'|'+name3+'|'+name4))

                                elif name1 and name2 and name3:
                                    url = cat3.xpath('a/@href').string()
                                    session.queue(Request(url, use='curl', force_charset='utf-8'), process_category, dict(cat=name1+'|'+name2+'|'+name3))

                    elif name1 and name2:
                        url = cat2.xpath('a/@href').string()
                        session.queue(Request(url, use='curl', force_charset='utf-8'), process_category, dict(cat=name1+'|'+name2))


def process_category(data, context, session):
    prods = data.xpath('//a[@data-product-link]')
    for prod in prods:
        name = prod.xpath('text()').string(multiple=True)
        manufacturer = prod.xpath('span/text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, manufacturer=manufacturer, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_category, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('p', '')
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = context['manufacturer']

    mpn = data.xpath('//div/@data-sku').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//div[@class="b-product-sku" and contains(., "EAN")]/div/text()').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    revs_cnt = data.xpath('//div[contains(@class, "rating")]/span/span/text()').string()
    if revs_cnt and int(revs_cnt.split()[0]) > 0:
        revs_url = 'https://widget.trustpilot.com/trustbox-data/5717796816f630043868e2e8?businessUnitId=46db331e00006400050113a8&locale=nb-NO&sku={}&reviewsPerPage=10'.format(mpn)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, revs_cnt=int(revs_cnt.split()[0]), mpn=mpn))


def process_reviews(data, context, session):
    product = context['product']

    try:
        revs = simplejson.loads(data.content).get('productReviews', {}).get('reviews', [])
    except:
        return

    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('id')

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('consumer', {}).get('displayName')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('stars')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        grades = rev.get('attributes')
        for grade_name, grade_val in grades.items():
            if grade_val and float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

        excerpt = rev.get('content')
        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').strip()
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 10
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        revs_url = 'https://widget.trustpilot.com/trustbox-data/5717796816f630043868e2e8?businessUnitId=46db331e00006400050113a8&locale=nb-NO&sku={mpn}&reviewsPerPage=10&page={page}'.format(mpn=context['mpn'], page=next_page)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, offset=offset, page=next_page, product=product))

    elif product.reviews:
        session.emit(product)
