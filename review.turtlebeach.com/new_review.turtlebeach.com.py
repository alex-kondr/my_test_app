from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Outlet']


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
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.turtlebeach.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[contains(@class, "category-card-category-card")]')
    for cat in cats:
        name = cat.xpath('span/text()').string()
        url = cat.xpath('a/@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-card-details-top")]')
    for prod in prods:
        name = prod.xpath('h2/text()').string()
        url = prod.xpath('a/@href').string().split('?')[0]
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = 'https://www.turtlebeach.com/api/collection-filter?handle=' + data.response_url.split('/')[-1]
    session.queue(Request(next_url), process_prodlist_next, dict(context))


def process_prodlist_next(data, context, session):
    prods = simplejson.loads(data.content).get('products', [])
    for prod in prods:
        name = prod.get('name')
        url = 'https://www.turtlebeach.com/products/' + prod.get('handle')
        session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name'] or data.xpath('//div[@role="presentation"]/span/text()').string()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].split('?')[0]
    product.manufacturer = 'Turtle Beach'

    product.category = context['cat']
    platforms = data.xpath('//div[p[contains(., "Platform")]]//button/div/text()').strings()
    if platforms:
        product.category += "|" + "/".join(platforms)

    mpn = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if mpn:
        mpn = mpn.split('sku":"')[-1].split('","')[0]
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//div/@data-yotpo-product-id').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

        revs_url = 'https://api-cdn.yotpo.com/v3/storefront/store/nO2yjgOHmfFpaM5z1vmPsjWPIde6ptX61rA6IEke/product/{ean}/reviews?page=1&perPage=5&sort=date,rating,badge,images'.format(ean=ean)
        session.do(Request(revs_url), process_reviews, dict(product=product, ean=ean))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    prod_ssid = revs_json.get('products', [{}])[0].get('id')
    if prod_ssid:
        product.ssid = str(prod_ssid)
        product.sku = product.ssid

    revs = revs_json.get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('user', {}).get('displayName')
        author_ssid = rev.get('user', {}).get('userId')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=str(author_ssid)))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('score')
        if grade_overall and grade_overall > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        grades = rev.get('customFields', {})
        if grades:
            for grade in grades.values():
                grade_name = grade.get('title')
                grade_val = grade.get('value')
                if grade_name and grade_val and grade_val > 0:
                    review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

        help_yes = rev.get('votesUp')
        if help_yes and help_yes > 0:
            review.add_property(type='helpful_votes', value=help_yes)

        help_no = rev.get('votesDown')
        if help_no and help_yes > 0:
            review.add_property(type='not_helpful_votes', value=help_no)

        is_verified_buyer = rev.get('verifiedBuyer')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('title')
        excerpt = rev.get('content')
        if excerpt and len(excerpt.strip(' +-.,')) > 1 and title:
            review.title = remove_emoji(title).strip(' +-.\n')
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', ' ').strip(' +-.\n')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = revs_json.get('pagination', {}).get('total')
    offset = context.get('offset', 0) + 5
    if offset < revs_cnt:
        next_page = context.get('page', 1) + 1
        next_url = 'https://api-cdn.yotpo.com/v3/storefront/store/nO2yjgOHmfFpaM5z1vmPsjWPIde6ptX61rA6IEke/product/{ean}/reviews?page={next_page}&perPage=5&sort=date,rating,badge,images'.format(ean=context['ean'], next_page=next_page)
        session.do(Request(next_url), process_reviews, dict(context, product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
