from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Deals']


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


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=9000)]
    session.queue(Request('https://www.dinotech.org/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//ul[@id="navDropdown0"]/li[@class="level0"]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('ul/li[contains(@class, "level1")]')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a/text()').string()

                subcats = cat1.xpath('ul/li[contains(@class, "level2")]/a')
                if subcats:
                    for subcat in subcats:
                        subcat_name = subcat.xpath('text()').string()
                        url = subcat.xpath('@href').string()
                        session.queue(Request(url + '?sorting=item.feedbackDecimal_desc'), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                else:
                    url = cat1.xpath('a/@href').string()
                    session.queue(Request(url + '?sorting=item.feedbackDecimal_desc'), process_prodlist, dict(cat=name+'|'+cat1_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//ul[contains(@class, "row product-list")]/li')
    for prod in prods:
        name = prod.xpath('a/span/text()').string()
        url = 'https://www.dinotech.org/' + prod.xpath('a/@href').string().split('/')[-1]

        revs_cnt = prod.xpath('.//div[contains(@class, "feedback-stars-background")]/span/text()').string()
        if revs_cnt:
            revs_cnt = int(revs_cnt.strip('( )'))
            if revs_cnt > 0:
                session.queue(Request(url), process_product, dict(context, name=name, url=url, revs_cnt=revs_cnt))
            else:
                return
        else:
            return

    next_url = data.xpath('//a[@aria-label="Zur nächsten Seite"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//single-item/@__item-id').string()
    product.sku = product.ssid
    product.category = context['cat']

    try:
        prod_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
        prod_json = simplejson.loads(prod_json)

        product.sku = prod_json.get('@id')
        product.manufacturer = prod_json.get('manufacturer', {}).get('name')
    except:
        pass

    ean = data.xpath('''//script[contains(., 'GTIN_13","code":"')]/text()''').string()
    if ean:
        ean = ean.split('GTIN_13","code":"')[-1].split('"}')[0]
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_url = 'https://www.dinotech.org/rest/feedbacks/feedback/helper/feedbacklist/' + product.ssid + '/1?feedbacksPerPage=10'
    session.do(Request(revs_url, force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('feedbacks', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('authorName') or rev.get('sourceRelation', [{}])[0].get('sourceRelationLabel')
        if author:
            author = remove_emoji(author).strip('*+=-_\n ')
            if author:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('feedbackRating', {}).get('rating', {}).get('ratingValue')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        title = rev.get('title')
        excerpt = rev.get('feedbackComment', {}).get('comment', {}).get('message')
        if excerpt and len(remove_emoji(excerpt).replace('\r', '').replace('\n', ' ').strip('*+=-_\n ')) > 2:
            if title:
                review.title = remove_emoji(title).replace('\r', '').replace('\n', ' ').strip('*+=-_\n ')

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\r', '').replace('\n', ' ').strip('*+=-_\n ')
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 10
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        revs_url = 'https://www.dinotech.org/rest/feedbacks/feedback/helper/feedbacklist/%s/%s?feedbacksPerPage=10' % (product.ssid, next_page)
        session.do(Request(revs_url, force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
