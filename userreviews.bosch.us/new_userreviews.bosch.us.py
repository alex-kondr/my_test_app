from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Home', 'Service', 'About', 'Trade Solutions', 'New Products']


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
    session.queue(Request('https://www.boschtools.com/us/en/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[regexp:test(@class, "item--dropdown|mainNavigation__item")]')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        if name not in XCAT:
            sub_cats = cat.xpath('ul/li//div[contains(@class, "col--item")]')
            if sub_cats:
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath('div/text()').string(multiple=True)
                    url = sub_cat.xpath('a/@href').string()

                    if sub_name not in XCAT:
                        session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name.title()))
            else:
                url = cat.xpath('a/@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    revs = data.xpath('//div[@data-sku]/a')
    for rev in revs:
        mpn = rev.xpath('@data-track_dyn_productid').string()
        name = rev.xpath('@title').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, mpn=mpn, url=url))

    next_url = data.xpath('//button[@aria-label="next"]/@data-href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div/@data-bv-product-id').string()
    product.sku = product.ssid
    product.category = context['cat']

    if context['mpn']:
        product.add_property(type='id.manufacturer', value=context['mpn'])

    prod_json = data.xpath('''//script[contains(., '"@type": "Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')

    revs_url = 'https://api.bazaarvoice.com/data/batch.json?passkey=mjblnkm24y2ynloumt11jaemk&apiversion=5.5&displaycode=4502-en_us&incentivizedstats=true&resource.q0=products&filter.q0=id%3Aeq%3A{ssid}&stats.q0=reviews&filteredstats.q0=reviews&filter_reviews.q0=contentlocale%3Aeq%3Aen_US&filter_reviewcomments.q0=contentlocale%3Aeq%3Aen_US&resource.q1=reviews&filter.q1=isratingsonly%3Aeq%3Afalse&filter.q1=productid%3Aeq%3A{ssid}&filter.q1=contentlocale%3Aeq%3Aen_US&sort.q1=submissiontime%3Adesc&stats.q1=reviews&filteredstats.q1=reviews&include.q1=authors%2Cproducts%2Ccomments&filter_reviews.q1=contentlocale%3Aeq%3Aen_US&filter_reviewcomments.q1=contentlocale%3Aeq%3Aen_US&filter_comments.q1=contentlocale%3Aeq%3Aen_US&limit.q1=8&offset.q1=0&limit_comments.q1=3&callback=BV._internal.dataHandler0'.format(ssid=product.ssid)
    session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content.replace('BV._internal.dataHandler0(', '').strip('( )')).get('BatchedResults', {}).get('q1', {})

    revs = revs_json.get('Results', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        date = rev.get('SubmissionTime')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('UserNickname')
        author_ssid = rev.get('AuthorId')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=author_ssid))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('RatingRange')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        grades = rev.get('SecondaryRatings')
        for grade_name, grade_info in grades.items():
            grade_val = grade_info.get('Value')
            if grade_name and grade_val and float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

        is_recommended = rev.get('IsRecommended')
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        hlp_yes = rev.get('TotalPositiveFeedbackCount')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('TotalNegativeFeedbackCount')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.get('Title')
        excerpt = rev.get('ReviewText')
        if excerpt and len(remove_emoji(excerpt).replace('\n', '').replace('\r', '').replace('  ', ' ').strip()) > 2:
            if title:
                review.title = remove_emoji(title).replace('\n', '').replace('\r', '').replace('  ', ' ').strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').replace('\r', ' ').replace('  ', ' ').strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = revs_json.get('TotalResults')
    offset = context.get('offset', 0) + 8
    if offset < revs_cnt:
        next_url = 'https://api.bazaarvoice.com/data/batch.json?passkey=mjblnkm24y2ynloumt11jaemk&apiversion=5.5&displaycode=4502-en_us&incentivizedstats=true&resource.q0=products&filter.q0=id%3Aeq%3A{ssid}&stats.q0=reviews&filteredstats.q0=reviews&filter_reviews.q0=contentlocale%3Aeq%3Aen_US&filter_reviewcomments.q0=contentlocale%3Aeq%3Aen_US&resource.q1=reviews&filter.q1=isratingsonly%3Aeq%3Afalse&filter.q1=productid%3Aeq%3A{ssid}&filter.q1=contentlocale%3Aeq%3Aen_US&sort.q1=submissiontime%3Adesc&stats.q1=reviews&filteredstats.q1=reviews&include.q1=authors%2Cproducts%2Ccomments&filter_reviews.q1=contentlocale%3Aeq%3Aen_US&filter_reviewcomments.q1=contentlocale%3Aeq%3Aen_US&filter_comments.q1=contentlocale%3Aeq%3Aen_US&limit.q1=8&offset.q1={offset}&limit_comments.q1=3&callback=BV._internal.dataHandler0'.format(ssid=product.ssid, offset=offset)
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, offset=offset))

    elif product.reviews:
        session.emit(product)
