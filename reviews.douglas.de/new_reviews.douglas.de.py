from agent import *
from models.products import *
import simplejson
import httplib
import re


httplib._MAXHEADERS = 1000


XCAT = ['MARKEN', 'OSTERN', 'SALE', 'Nachhaltigkeit', 'LUXUS', 'NEU', 'Beauty-Storys', 'Douglas Beauty Tester', 'NEU Parfum', 'SALE Parfum']


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
    session.queue(Request('https://www.douglas.de/de', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@class="navigation-main-entry" and .//a[normalize-space()]]')
    for cat in cats:
        name = cat.xpath('.//a[contains(@class, "navigation-main-entry__link")]/text()').string()
        sub_cats_id = cat.xpath('@data-uid').string()

        if name not in XCAT:
            url = 'https://www.douglas.de/api/v2/navigation/nodes/{sub_cats_id}/children'.format(sub_cats_id=sub_cats_id)
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    sub_cats_json = simplejson.loads(data.content)

    sub_cats = sub_cats_json.get('nodes', [])
    for sub_cat in sub_cats:
        sub_name = sub_cat.get('title')

        sub_cats1 = sub_cat.get('children', [])
        if sub_cats1 and sub_name not in XCAT:
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.get('title')
                url_data = sub_cat.get('entries')

                if url_data and len(url_data) > 0:
                    url = 'https://www.douglas.de' + url_data[0].get('component', {}).get('otherProperties', {}).get('url')

                    if sub_name1 and 'All' not in sub_name1 and 'ALL' not in sub_name1 and 'Tutorial' not in sub_name1:
                        session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + sub_name + '|' + sub_name1))
                    else:
                        url = 'https://www.douglas.de' + sub_cat.get('entries', [{}])[0].get('component', {}).get('otherProperties', {}).get('url')
                        session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + sub_name))

        elif sub_name not in XCAT:
            url_data = sub_cat.get('entries')
            if url_data and len(url_data) > 0:
                url = 'https://www.douglas.de' + url_data[0].get('component', {}).get('otherProperties', {}).get('url')
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-grid-column")]')
    for prod in prods:
        name = prod.xpath('.//div[@class="text brand-line" or @class="text name"]//text()').string(multiple=True)
        manufacturer = prod.xpath('.//div[@class="text top-brand"]/text()').string()
        url = prod.xpath('.//a[@linkappearance="true"]/@href').string().split('?')[0]

        revs_cnt = prod.xpath('.//span[@data-testid="ratings-info"]')
        if revs_cnt:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, manufacturer=manufacturer, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat']
    product.manufacturer = context['manufacturer']
    product.sku = data.xpath('//div[contains(., "Art-Nr.")]/span[@class="classification__item"]/text()').string()

    revs_url = 'https://www.douglas.de/jsapi/v2/products/bazaarvoice/reviews?baseProduct=' + product.ssid
    session.do(Request(revs_url, use='curl', force_charset='utf-8'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    revs = revs_json.get('Results', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('submissionTime')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('userNickname')
        author_id = rev.get('authorId')
        if author and author_id:
                review.authors.append(Person(name=author, ssid=author_id))
        elif author:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.get('totalPositiveFeedbackCount')
        if hlp_yes and hlp_yes > 0:
            review.add_property(type='helpful_votes', value=hlp_yes)

        hlp_no = rev.get('totalNegativeFeedbackCount')
        if hlp_no and hlp_no > 0:
            review.add_property(type='not_helpful_votes', value=hlp_no)

        title = rev.get('title')
        if title:
            title = remove_emoji(title).strip()

        excerpt = rev.get('reviewText')
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt)
            excerpt = excerpt.replace('[Diese Bewertung wurde nach Erhalt eines Anreizes (Gutschein, Rabatt, kostenlose Probe, Gewinnspiel, Wettbewerb mit Verlosung, etc.) eingereicht.]', '').replace('\n', ' ').strip()

            if excerpt and len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = rev.get('id')
                if not review.ssid:
                    review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 10
    revs_cnt = revs_json.get('TotalResults')
    if offset < revs_cnt:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.douglas.de/jsapi/v2/products/bazaarvoice/reviews?baseProduct={ssid}&page={page}'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url, use='curl', force_charset='utf-8'), process_reviews, dict(product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
