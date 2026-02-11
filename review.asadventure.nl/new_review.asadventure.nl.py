from agent import *
from models.products import *
import simplejson
import re


XCAT = ["Nieuwe collectie", "Nieuwe outdoorcollectie", "Nieuwe fashioncollectie", "Verhuur", "Ecocheque producten", "Professioneel", "Promoties", "Veilig in het verkeer", "Cadeautips", "Merken", "Inspiratie", "✨ Nieuwe collectie"]


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
    session.queue(Request('https://www.asadventure.com/nl.html', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, contenxt, session):
    cats = data.xpath('//div[contains(@class, "category-flyout__menu")]')
    for cat in cats:
        name = cat.xpath('div[contains(@class, "title")]/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('ul[contains(@class, "category-flyout__menu")]')
            for cat1 in cats1:
                cat1_name = cat1.xpath('li[contains(@class, "menu-item")]/a/text()').string()

                if cat1_name not in XCAT:
                    subcats = cat1.xpath('li[not(contains(@class, "menu-item"))]/a')

                    for subcat in subcats:
                        subcat_name = subcat.xpath('text()').string()
                        url = subcat.xpath('@href').string()

                        if subcat_name not in XCAT:
                            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-tile--vertical")]')
    for prod in prods:
        url = prod.xpath('(span/a|a)/@href').string().split('?')[0]

        revs_cnt = prod.xpath('.//div[contains(@class, "rating")]//span[contains(@class, "subtle")]/text()').string()
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[@data-testid="product_brand"]//text()').string()

    product.name = data.xpath('//div[h1[@data-testid="product_name"]]/span[@itemprop="item"]/text()').string()
    if not product.name:
        product.name = data.xpath('//div[h1[@data-testid="product_name"]]/text()').string()

    prod_info = data.xpath("//script[contains(., 'var productInfo = ')]/text()").string()
    if prod_info:
        prod_info = simplejson.loads(prod_info.split(' = ')[-1])
        product.ssid = prod_info.get("productId")
        product.sku = product.ssid

    mpn = data.xpath('//div/@data-parent-product-sku').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

        revs_url = 'https://api.feefo.com/api-feefo/api/10/reviews/product?parent_product_sku={}&origin=www.asadventure.com&merchant_identifier=as-adventure&page_size=5'.format(mpn)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, mpn=mpn))


def process_reviews(data, context, session):
    product = context['product']

    try:
        revs_json = simplejson.loads(data.content)
    except:
        return

    revs = revs_json.get('reviews', [])
    for rev in revs:
        if rev.get('locale') != 'nl_NL':
            continue

        rev = rev.get('products', [{}])[0]

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('id')

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        grade_overall = rev.get('rating', {}).get('rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('feedbackVerificationState')
        if is_verified_buyer and is_verified_buyer == 'feefoVerified':
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('helpful_votes')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        excerpt = rev.get('review')
        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').replace('\r', '').strip()
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    revs_cnt = revs_json.get('summary', {}).get('meta', {}).get('count')
    if offset < revs_cnt:
        next_page = context.get('page', 1) + 1
        revs_url = 'https://api.feefo.com/api-feefo/api/10/reviews/product?parent_product_sku={mpn}&origin=www.asadventure.com&merchant_identifier=as-adventure&page_size=5&page={page}'.format(mpn=context['mpn'], page=next_page)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
