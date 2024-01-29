from agent import *
from models.products import *
import simplejson, re


XCATS = ['Sale Artikel']


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
    session.queue(Request('https://www.matratzen-concord.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="row navigation-flyout-categories is-level-0"]')
    for cat in cats:
        cats_ = cat.xpath('.//div[@class="navigation-flyout-col"]')
        name = cats_[0].xpath('.//span/text()').string().replace('Alle ', '')

        if name not in XCATS:
            for sub_cat in cats_[1:]:
                sub_name = sub_cat.xpath('.//span/text()').string().replace('Alle ', '')
                url = sub_cat.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name, prods_url=url))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="card-body"]')
    for prod in prods:
        name = prod.xpath('.//a[@class="product-name"]/text()').string()
        url = prod.xpath('.//a/@href').string()

        revs_cnt = prod.xpath('.//span[@class="rating-count"]/text()').string()
        if revs_cnt:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_page = data.xpath('//li[@class="page-item page-next"]/input/@value').string()
    if next_page:
        next_url = context['prods_url'] + '?p=' + next_page
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1]
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[@itemprop="name"]/@content').string()

    mpn = data.xpath('//span[@itemprop="sku"]/strong/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    is_verified_buyer = data.xpath('//script[contains(., "Von verifiziertem Käufer")]')

    prod_id = data.xpath('//script[contains(., "parentID")]/text()').string()
    if prod_id:
        prod_id = prod_id.split("parentID = '")[-1].split("';")[0]
        url = 'https://www.matratzen-concord.de/ratings/trustedshops/' + prod_id
        session.queue(Request(url), process_reviews, dict(product=product, is_verified_buyer=is_verified_buyer))


def process_reviews(data, context, session):
    product = context['product']

    revs = simplejson.loads(data.content).get('reviews', {})
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('submittedAt')
        if date:
            review.date = date.split('T')[0]

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        if context.get('is_verified_buyer'):
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('title')
        if title:
            title = remove_emoji(title.replace('..', ''))

        excerpt = rev.get('comment')
        if excerpt:
            review.title = title

            excerpt = excerpt.replace('..', '')
            excerpt = remove_emoji(excerpt)

        elif title:
            excerpt = title

        if excerpt and len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # no next page
