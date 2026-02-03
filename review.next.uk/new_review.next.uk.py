from agent import *
from models.products import *
import simplejson
import re


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
    session.queue(Request('https://www.next.co.uk/shop/department-homeware-productaffiliation-kitchen-0'), process_category, dict(cat='Home|Kitchen & Dining'))
    session.queue(Request('https://www.next.co.uk/shop/department-homeware-productaffiliation-lighting-0'), process_category, dict(cat='Home|Lighting'))


def process_category(data, context, session):
    cats = data.xpath('//ul/li/a[contains(@href, "category-")]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string() + '?p=1'
        session.queue(Request(url, max_age=0), process_prodlist, dict(cat=context['cat']+'|'+name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@data-testid, "product_tile")]')
    for prod in prods:
        name = prod.xpath('div/@aria-label').string()
        url = prod.xpath('a[contains(@data-testid, "_link")]/@href').string().split('#')[0]

        rating = prod.xpath('.//span[contains(@data-testid, "star-rating")]')
        if rating:
            session.queue(Request(url, max_age=0), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[regexp:test(., "view next", "i")]/@href').string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat']

    prod_json = data.xpath('//script[@data-testid="pdp-structured-data"]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)
        product.manufacturer = prod_json.get('brand', {}).get('name')
        product.sku = prod_json.get('sku', product.ssid)

    options = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0' -H 'Accept: */*' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Referer: https://www.next.co.uk/' -H 'Bv-Bfd-Token: 24381,main_site,en_GB' -H 'Origin: https://www.next.co.uk' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: cross-site' -H 'Priority: u=0' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers'"""
    revs_url = 'https://apps.bazaarvoice.com/bfd/v1/clients/next_com/api-products/cv2/resources/data/reviews.json?resource=reviews&action=REVIEWS_N_STATS&filter=productid%3Aeq%3A{ssid}&filter=contentlocale%3Aeq%3Aen_GB%2Cen_GB&filter=isratingsonly%3Aeq%3Afalse&filter_reviews=contentlocale%3Aeq%3Aen_GB%2Cen_GB&include=authors%2Cproducts%2Ccomments&filteredstats=reviews&Stats=Reviews&limit=30&offset=0&limit_comments=3&sort=submissiontime%3Adesc&apiversion=5.5&displaycode=24381-en_gb'.format(ssid=product.ssid)
    session.do(Request(revs_url, use='curl', options=options, max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content).get('response')

    revs = revs_json.get('Results', [])
    for rev in revs:
        if rev.get('ContentLocale') != 'en_GB' or rev.get('IsSyndicated'):
            continue

        review = Review()
        review.type = 'user'
        review.ssid = rev.get('Id')
        review.url = product.url

        date = rev.get('SubmissionTime')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('UserNickname')
        author_ssid = rev.get('AuthorId')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=author_ssid))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('Rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        grades = rev.get('SecondaryRatings', {})
        for grade in grades.values():
            grade_name = grade.get('Id')
            grade_val = grade.get('Value')
            if grade_name and grade_val and float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

        hlp_yes = rev.get('TotalPositiveFeedbackCount')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('TotalNegativeFeedbackCount')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        is_recommended = rev.get('IsRecommended')
        if is_recommended:
            review.add_property(value=True, type='is_recommended')

        title = rev.get('Title')
        excerpt = rev.get('ReviewText')
        if excerpt and len(remove_emoji(excerpt).replace('\n', '').strip(' .+-*')) > 2:
            if title:
                review.title = remove_emoji(title).replace('\n', '').replace('\r', ' ').strip(' .+-*')
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').replace('\r', ' ').strip(' .+-*')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = revs_json.get('TotalResults', 0)
    offset = context.get('offset', 0) + 30
    if offset < revs_cnt:
        options = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0' -H 'Accept: */*' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Referer: https://www.next.co.uk/' -H 'Bv-Bfd-Token: 24381,main_site,en_GB' -H 'Origin: https://www.next.co.uk' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: cross-site' -H 'Priority: u=0' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers'"""
        revs_url = 'https://apps.bazaarvoice.com/bfd/v1/clients/next_com/api-products/cv2/resources/data/reviews.json?resource=reviews&action=REVIEWS_N_STATS&filter=productid%3Aeq%3A{ssid}&filter=contentlocale%3Aeq%3Aen_GB%2Cen_GB&filter=isratingsonly%3Aeq%3Afalse&filter_reviews=contentlocale%3Aeq%3Aen_GB%2Cen_GB&include=authors%2Cproducts%2Ccomments&filteredstats=reviews&Stats=Reviews&limit=30&offset={offset}&limit_comments=3&sort=submissiontime%3Adesc&apiversion=5.5&displaycode=24381-en_gb'.format(ssid=product.ssid, offset=offset)
        session.do(Request(revs_url, use='curl', options=options, max_age=0), process_reviews, dict(context, product=product, offset=offset))

    elif product.reviews:
        session.emit(product)
