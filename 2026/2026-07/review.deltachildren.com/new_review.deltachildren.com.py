from agent import *
from models.products import *
import simplejson
import re


XCAT = ["Nursery Sets", "Kids' Bedroom Sets", 'Shop by Character']


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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.deltachildren.com/', use='curl', force_charset='utf-8'), process_frontpage, dict())
    session.queue(Request('https://www.deltachildren.com/collections/wagons', use='curl', force_charset='utf-8'), process_prodlist, dict(cat='Wagons'))


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//ul[li[contains(@class, "site-header__nav-item--bottom")]]')
    for cat in cats:
        name = cat.xpath('(li[contains(@class, "site-header__nav-item--bottom")]/a)[last()]/text()').string()

        subcats = cat.xpath('li[contains(@class, "site-header__nav-subitem--mega")]')
        for subcat in subcats:
            subcat_name = subcat.xpath('text()').string(multiple=True)
            url = subcat.xpath('a/@href').string()

            if subcat_name not in XCAT:
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//a[contains(@class, "product__title")]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string().split('?')[0].split('#')[0]
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

# no next page


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div/@data-id').string()
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = 'Delta Children'

    mpn = data.xpath('//span[@id="display_sku"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//span[@id="display_upc"]/text()').string()
    if ean and ean.isdigit() and len(ean) > 11:
        product.add_property(type='id.ean', value=ean)

    revs_cnt = data.xpath('//span[@class="jdgm-prev-badge__text"]/text()').string()
    if revs_cnt:
        revs_cnt = revs_cnt.replace('reviews', '').strip()
        if revs_cnt.isdigit() and int(revs_cnt) > 0:
            revs_url = 'https://judge.me/reviews/reviews_for_widget?url=deltachildrenstore.myshopify.com&shop_domain=deltachildrenstore.myshopify.com&platform=shopify&per_page=5&product_id=' + product.ssid
            session.do(Request(revs_url, use='curl', max_age=0, force_charset='utf-8'), process_reviews, dict(product=product, revs_cnt=int(revs_cnt)))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    try:
        new_data = simplejson.loads(data.content).get('html', '')
        revs = data.parse_fragment(new_data).xpath('//div[contains(@class, "reviews")]/div')
    except:
        revs = []

    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@data-review-id').string()

        date = rev.xpath('.//span/@data-content').string()
        if date:
            review.date = date.split()[0]

        author = rev.xpath('.//span[contains(@class, "rev__author")]//text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span/@data-score').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('@data-verified-buyer').string()
        if is_verified == 'true':
            review.add_property(type='is_verified_buyer', value=is_verified)

        hlp_yes = rev.xpath('@data-thumb-up-count').string()
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('@data-thumb-down-count').string()
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.xpath('.//b[contains(@class, "rev__title")]/text()').string()
        excerpt = rev.xpath('.//div[contains(@class, "rev__body")]//text()').string(multiple=True)
        if excerpt and len(remove_emoji(excerpt).replace('\n', '').replace('\r', '').replace('\t', '').strip(' .+-')) > 1:
            if title:
                review.title = remove_emoji(title).strip(' .+-\n\r')
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').replace('\r', '').replace('\t', '').strip(' .+-')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        revs_url = 'https://judge.me/reviews/reviews_for_widget?url=deltachildrenstore.myshopify.com&shop_domain=deltachildrenstore.myshopify.com&platform=shopify&per_page=5&product_id={ssid}&page={page}'.format(ssid=product.ssid, page=next_page)
        session.do(Request(revs_url, use='curl', max_age=0, force_charset='utf-8'), process_reviews, dict(context, product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
