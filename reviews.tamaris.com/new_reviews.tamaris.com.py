from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Neuheiten', 'Kollektionen', 'Sale']


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
    session.queue(Request('https://tamaris.com/de-CH/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "dropdown-level-1")]')
    for cat in cats:
        name = cat.xpath('a/span/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('.//ul[contains(@class, "dropdown-level-2")]/li')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('div/span/text()').string()

                if sub_name not in XCAT:
                    sub_cats1 = sub_cat.xpath('.//li[@class="dropdown-item"]')
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('a/span/text()').string()
                        url = sub_cat1.xpath('a/@href').string()

                        if 'All' not in sub_name1:
                            session.queue(Request(url + '?sz=48'), process_prodlist, dict(cat=name + '|' + sub_name1))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@data-ean]')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('.//div[contains(@class, "product-name")]/text()').string()
        product.ssid = prod.xpath('@data-uuid').string()
        product.sku = product.ssid
        product.url = prod.xpath('.//a[@class="tile-link"]/@href').string()
        product.manufacturer = 'Tamaris'
        product.category = context['cat']

        ean = prod.xpath('@data-ean').string()
        if ean:
            product.add_property(type='id.ean', value=ean)

        mpn = prod.xpath('@data-product-id').string()
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

            revs_url = 'https://cdn-ws.turnto.eu/v5/sitedata/7ow2UbXsJQJAP18site/{mpn}/r/relatedReview/de_CH/0/9999/RECENT?'.format(mpn=mpn)
            session.queue(Request(revs_url), process_reviews, dict(product=product, mpn=mpn))

    next_url = data.xpath('//a[contains(@class, "load-more-results")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    revs = revs_json.get('reviews')
    for rev in revs:
        if rev.get('locale') != 'de_CH' and rev.get('locale') != 'de_DE':
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.get('dateCreatedFormatted')

        author = (rev.get('user', {}).get('firstName', '') + ' ' + rev.get('user', {}).get('lastName', '')).strip()
        author_ssid = rev.get('user', {}).get('id')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=str(author_ssid)))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.get('upVotes')
        if hlp_yes and hlp_yes > 0:
            review.add_property(type='helpful_votes', value=hlp_yes)

        hlp_no = rev.get('downVotes')
        if hlp_no and hlp_no > 0:
            review.add_property(type='not_helpful_votes', value=hlp_yes)

        is_recommended = rev.get('recommended')
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        is_verified_buyer = rev.get('purchaseDateFormatted')
        if is_verified_buyer and len(is_verified_buyer) > 2:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('title')
        excerpt = rev.get('text')
        if excerpt and len(excerpt) > 1:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt.replace('<br />', ''))

            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                ssid = rev.get('id')
                if review.ssid:
                    review.ssid = str(ssid)
                else:
                    review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page