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
    cats = data.xpath('//ul[@id="navDropdown0"]/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()
        if name not in XCAT:
            cats1 = cat.xpath('ul/li')
            for cat1 in cats1:
                name1 = cat1.xpath('a/text()').string()
                url = cat1.xpath('a/@href').string()
                cats2 = cat1.xpath('ul/li/a')
                if not cats2:
                    session.queue(Request(url + '?items=75&sorting=item.feedbackDecimal_desc'), process_prodlist, dict(cat=name+'|'+name1))

                for cat2 in cats2:
                    name2 = cat2.xpath('text()').string()
                    url = cat2.xpath('@href').string()
                    session.queue(Request(url + '?items=75&sorting=item.feedbackDecimal_desc'), process_prodlist, dict(cat=name+'|'+name1+'|'+name2))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//ul[contains(@class, "product-list")]/li')
    for prod in prods:
        name = prod.xpath('a/span/text()').string()
        url = prod.xpath('a/@href').string()

        revs_cnt = prod.xpath('.//div[contains(@class, "feedback-stars")]/span/text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            url = 'https://www.dinotech.org/' + url.split('/')[-1]
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.ssid = data.xpath('//body[contains(@class, "page-singleitem")]/@class').string().split('item-')[-1].split()[0]
    product.sku = product.ssid

    prod_json = data.xpath('''//script[contains(., '"Product",')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)
        product.manufacturer = prod_json.get('manufacturer', {}).get('name')

    ean = data.xpath('''//script[contains(., 'GTIN_13","code":"')]/text()''').string()
    if ean:
        ean = ean.split('GTIN_13","code":"')[-1].split('"}')[0]
        if ean and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_url = 'https://www.dinotech.org/rest/feedbacks/feedback/helper/feedbacklist/' + product.ssid + '/1?feedbacksPerPage=10'
    session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    revs = revs_json.get('feedbacks', [])
    for rev in revs:
        review = Review()
        review.url = product.url
        review.type = 'user'

        author = rev.get('authorName')
        if not author:
            author = rev.get('sourceRelation', [{}])[0].get('sourceRelationLabel')
        if author:
            author = remove_emoji(author).strip('*+=-_\n ')
            if author:
                review.authors.append(Person(name=author, ssid=author))

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        grade_overall = rev.get('feedbackRating', {}).get('rating', {}).get('ratingValue')
        if grade_overall and int(grade_overall) > 0:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        excerpt = rev.get('feedbackComment', {}).get('comment', {}).get('message')
        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\r', '').replace('\n', ' ').strip('*+=-_\n ')
            if excerpt:
                review.properties.append(ReviewProperty(type="excerpt", value=excerpt))
                review.ssid = review.digest() if author else review.digest(excerpt)
                product.reviews.append(review)

    is_last_page = revs_json.get('pagination', {}).get('isLastPage')
    if not is_last_page:
        next_page = context.get('page', 1) + 1
        revs_url = 'https://www.dinotech.org/rest/feedbacks/feedback/helper/feedbacklist/%s/%s?feedbacksPerPage=10' % (product.ssid, next_page)
        session.do(Request(revs_url), process_reviews, dict(product=product, page=next_page))
    elif product.reviews:
        session.emit(product)