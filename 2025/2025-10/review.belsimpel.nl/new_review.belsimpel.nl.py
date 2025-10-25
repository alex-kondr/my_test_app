from agent import *
from models.products import *
import re
import simplejson


XCAT = ['Weekdeals', 'Telefoon met abonnement', 'Sim Only', 'Verlengen', 'Klantenservice']


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


def process_get_token(data, context, session):
    return simplejson.loads(data.content).get('token')


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.belsimpel.nl'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//li[contains(@class, "desktop_nav_menu_item")]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name and name not in XCAT:
            sub_cats = cat.xpath('.//ul[not(regexp:test(., "Populaire|Alle providers"))]/li[not(contains(@class, "title"))]/a')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string().split('?')[0]
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//div[contains(@class, "product-item__title-rating")]')
    for prod in prods:
        name = prod.xpath('.//a/text()').string()
        url = prod.xpath('.//a/@href').string()

        revs_cnt = prod.xpath('.//span[contains(@class, "rating__review-amount")]/text()').string()
        if revs_cnt and int(revs_cnt.strip('( )')) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@aria-label="Volgende pagina"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    ssid = data.xpath('//script[contains(., "viewedProductId") and not(contains(., "null"))]/text()').string()
    if not ssid:
        return

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = ssid.split('=')[-1].strip('" ')
    product.sku = product.ssid
    product.category = context['cat']

    prod_json = data.xpath('''//script[contains(., '"@type": "Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')

        mpn = prod_json.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('gtin12')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    token = session.do(Request('https://www.belsimpel.nl/API/vergelijk/Exchange?response_type=token&client_id=nl.belsimpel.public.web&scope=Reviews', max_age=0), process_get_token, dict())
    revs_url = 'https://www.belsimpel.nl/API/Reviews/v1.0/ProductReviews/{}?locale=nl_NL'.format(product.ssid)
    options = "--compressed -H 'Accept-Encoding: deflate' -H 'Authorization: Bearer " + token + "'"
    session.do(Request(revs_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(product=product, token=token))

def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    if revs_json.get('status') != 'success':
        token = session.do(Request('https://www.belsimpel.nl/API/vergelijk/Exchange?response_type=token&client_id=nl.belsimpel.public.web&scope=Reviews', max_age=0), process_get_token, dict())
        revs_url = 'https://www.belsimpel.nl/API/Reviews/v1.0/ProductReviews/{}?locale=nl_NL'.format(product.ssid)
        options = "--compressed -H 'Accept-Encoding: deflate' -H 'Authorization: Bearer " + token + "'"
        session.do(Request(revs_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(context, token=token))
        return

    revs = revs_json.get('data', {}).get('review_list', [])
    if not revs:
        return

    for rev in revs:
        if str(rev.get('reviewed_item', {}).get('id')) != product.ssid:
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))
        review.date = rev.get('date')

        author = rev.get('review', {}).get('author')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('review', {}).get('label', {}).get('score', {}).get('raw')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

        pros_ = []
        pros = rev.get('review', {}).get('plus_points')
        if pros:
            for pro in pros:
                pro = remove_emoji(pro).strip(' +-*.:;•–')
                if len(pro) > 1 and pro not in pros_:
                    pros_.append(pro)
                    review.add_property(type='pros', value=pro)

        cons_ = []
        cons = rev.get('review', {}).get('min_points', [])
        if cons:
            for con in cons:
                con = remove_emoji(con).strip(' +-*.:;•–')
                if len(con) > 1 and con not in cons_:
                    cons_.append(con)
                    review.add_property(type='cons', value=con)

        is_recommended = rev.get('review', {}).get('is_would_recommend')
        if is_recommended and is_recommended is True:
            review.add_property(value=True, type='is_recommended')

        hlp_yes = rev.get('rating', {}).get('thumbs_up_count', {}).get('raw')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('rating', {}).get('thumbs_down_count', {}).get('raw')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_no))

        title = rev.get('review', {}).get('title')
        excerpt = rev.get('review', {}).get('description')
        if excerpt and len(remove_emoji(excerpt).replace('\r', '').replace('\n', '').strip()) > 2:
            if title:
                review.title = remove_emoji(title).strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\r', '').replace('\n', '').strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = revs_json.get('data', {}).get('reviews_available', {}).get('total', 0)
    offset = context.get('offset', 0) + 15
    if offset < int(revs_cnt):
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.belsimpel.nl/API/Reviews/v1.0/ProductReviews/{ssid}?locale=nl_NL&page={page}'.format(ssid=product.ssid, page=next_page)
        options = "--compressed -H 'Accept-Encoding: deflate' -H 'Authorization: Bearer " + context['token'] + "'"
        session.do(Request(next_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(context, product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
