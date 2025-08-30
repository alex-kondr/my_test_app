from agent import *
from models.products import *
import simplejson
import re

OPTIONS = "--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0' -H 'Accept: */*' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Authorization: Bearer sNwyPNK99inB57bez5vr9v0FcxBzkPXZjSUgbu+Aye90+BXkbeBUV0+YG2L/YFSMY7mGVQYxt1C3oRMtzzreTbZyl7gqFCaXfPboxH5niQxR4p/Be1giV/StJstZP+ktqaXpkt+Gva6Mt+nX+9N/2M3RoLPnYgt0uOmPezMfDy8NIC1pUBzLjeLhqhShf4ypgfEaMtva0e5nZzr7bfJu9aqi2L7N9tkEjxqvzobmwkMcoUfcXU3KJNzoMNpCpX5B3JwTW/UdGruOY26KtwdW6uFOo3KkwZ4Hfwl3RfMUamTiy3SkTWgF2L4TYzxYeZrWqfdYMHs=' -H 'Cookie: PHPSESSID=4bde1dee360fc68f350ee5c05cbdac1b; ABST=ABST.68b069c557de23.61518738; ab_store=36770b6008803620afbaef246afe6897; pref=sentry%2Clanguage_and_country%2Cshopping_cart%2Cauthentication%2Cimages%2Cfavourites%2Cabs%2Cgoogle_analytics%2Cpixels%2Cgoogle_analytics_remarketing; bs_viewed_product_ids=%7B%22162224%22%3A%7B%22id%22%3A162224%2C%22deleted%22%3Afalse%2C%22viewed%22%3A%5B1756443279669%5D%7D%2C%22172643%22%3A%7B%22id%22%3A172643%2C%22deleted%22%3Afalse%2C%22viewed%22%3A%5B1756443525123%2C1756444247391%5D%7D%7D'"

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
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request('https://www.belsimpel.nl/API/vergelijk/v1.4/WebSearch?resultaattype=hardware_only', use='curl', options=OPTIONS, force_charset='utf-8', max_age=0), process_prodlist, dict(cat='Handy', cat_id='hardware_only'))
    session.queue(Request('https://www.belsimpel.nl/API/vergelijk/v1.4/WebSearch?resultaattype=accessory_only', use='curl', options=OPTIONS, force_charset='utf-8', max_age=0), process_prodlist, dict(cat='Zubehör', cat_id='accessory_only'))
    session.queue(Request('https://www.belsimpel.nl/API/vergelijk/v1.4/WebSearch?resultaattype=tablet_only', use='curl', options=OPTIONS, force_charset='utf-8', max_age=0), process_prodlist, dict(cat='Tablets', cat_id='tablet_only'))


def process_prodlist(data, context, session):
    page_data = simplejson.loads(data.content)

    prods = page_data.get('results', [])
    for prod in prods:
        name = prod['pretty_name']
        link = prod['hardware']['url_path']
        url = 'https://www.belsimpel.nl' + link
        ssid = prod['hardware']['id']

        revs_cnt = prod['hardware'].get('review', {}).get('number_of_reviews', {}).get('raw')
        if revs_cnt and revs_cnt > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_product, dict(context, name=name, url=url, ssid=ssid))

    next_page = page_data.get('settings', {}).get('pagination', {}).get('convenience_pages', {}).get('next_page', {}).get('value')
    if next_page:
        next_url = 'https://www.belsimpel.nl/API/vergelijk/v1.4/WebSearch?resultaattype={}&pagina={}'.format(context['cat_id'], next_page)
        session.queue(Request(next_url, use='curl', options=OPTIONS, force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    prod_json = data.xpath('''//script[contains(., '"@type": "Product"')]/text()''').string()
    prod_json = simplejson.loads(prod_json)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = prod_json.get('brand', {}).get('name')
    product.ssid = context['ssid']

    ean = prod_json.get('gtin13')
    if ean:
        product.add_property(type='id.ean', value=str(ean))

    mpn = prod_json.get('sku')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn.strip(' \t'))

    revs_token = session.do(Request('https://www.belsimpel.nl/API/vergelijk/Exchange?response_type=token&client_id=nl.belsimpel.public.web&scope=Reviews', max_age=0), process_review_token, dict())
    options = "-H 'Authorization: Bearer {}'".format(revs_token)
    revs_url = 'https://www.belsimpel.nl/API/Reviews/v1.0/ProductReviews/{}?locale=nl_NL'.format(product.ssid)
    session.do(Request(revs_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(product=product, revs_url=revs_url, options=options))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('data', {}).get('review_list', [])
    if not revs:
        return

    for rev in revs:
        if str(rev.get('reviewed_item', {}).get('id', '')) != product.ssid:
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev['id'])
        review.date = rev.get('date')

        author = rev.get('review', {}).get('author')
        if author:
            author = remove_emoji(author).strip()
            if author:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('review', {}).get('label', []).get('score', {}).get('raw')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=10.0))

        pros = rev.get('review', {}).get('plus_points', [])
        if pros:
            for pro in pros:
                pro = remove_emoji(pro).strip(' \\.+-')
                if pro:
                    review.add_property(type='pros', value=pro)

        cons = rev.get('review', {}).get('min_points', [])
        if cons:
            for con in cons:
                con = remove_emoji(con).strip(' \\.+-')
                if con:
                    review.add_property(type='cons', value=con)

        is_recommended = rev.get('review', {}).get('is_would_recommend')
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        hlp_yes = rev.get('rating', {}).get('thumbs_up_count', {}).get('raw')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('rating', {}).get('thumbs_down_count', {}).get('raw')
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.get('review', {}).get('title')
        excerpt = rev.get('review', {}).get('description')
        if excerpt:
            if title:
                review.title = remove_emoji(title).strip()
        elif title:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', ''). replace('\r', '').strip(' +-.')
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                product.reviews.append(review)

    page = revs_json.get('data', {}).get('pagination', {}).get('page_current')
    last_page = revs_json.get('data', {}).get('pagination', {}).get('page_max')
    if page < last_page:
        revs_url = context['revs_url'] + '&page={}'.format(page+1)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', options=context['options'], max_age=0), process_reviews, dict(context))

    elif product.reviews:
        session.emit(product)


def process_review_token(data, context, session):
    revs_token = simplejson.loads(data.content)['token']
    return revs_token
