from agent import *
from models.products import *
import simplejson


XCAT = ["View the Milex Range", "Request Spares", "How to Guide", "Recipes"]


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
    session.queue(Request("https://milex.co.za/", use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//ul[@id="siteNav"]/li[contains(@class, "dropdown")]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        cats1 = cat.xpath('ul/li')
        for cat1 in cats1:
            cat1_name = cat1.xpath('a/text()').string()

            if cat1_name not in XCAT:
                subcats = cat1.xpath('ul/li/a')
                if subcats:
                    for subcat in subcats:
                        subcat_name = subcat.xpath('text()').string()
                        url = subcat.xpath('@href').string()
                        session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                else:
                    url = cat1.xpath('a/@href').string()
                    session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name+'|'+cat1_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//div[contains(@class, "products")]//div[@class="details"]')
    for prod in prods:
        name = prod.xpath('a[contains(@class, "title")]/text()').string()
        url = prod.xpath('a[contains(@class, "title")]/@href').string()

        revs_cnt = prod.xpath('.//div[@class="jdgm-prev-badge"]/@data-number-of-reviews').string()
        if revs_cnt:
            revs_cnt = int(revs_cnt)
            if int(revs_cnt) > 0:
                url = 'https://milex.co.za/products/' + url.split('/')[-1]
                session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url, revs_cnt=revs_cnt))

    # No next page


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div[contains(@class, "product")]/div[contains(@class, "jdgm")]/@data-id').string()
    product.category = context["cat"].replace('View our range', '').strip('| ')
    product.manufacturer = "Milex"

    mpn = data.xpath('//span[@class="variant-sku"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    prod_data = data.xpath("""//script[contains(., '"@type": "Product"')]//text()""").string()
    if prod_data:
        prod_data = simplejson.loads(prod_data)

        ean = prod_data.get('mpn')
        if ean and str(ean).isdigit() and len(str(ean)) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_url = "https://judge.me/reviews/reviews_for_widget?url=milex-south-africa.myshopify.com&shop_domain=milex-south-africa.myshopify.com&platform=shopify&page=1&per_page=10&product_id=" + product.ssid
    session.do(Request(revs_url, max_age=0, force_charset='utf-8'), process_reviews, dict(context, product=product))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context["product"]

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('reviews', [])
    for rev in revs:
        review = Review()
        review.url = product.url
        review.type = 'user'
        review.ssid = rev.get('uuid')

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('reviewer_name')
        if author:
            author = remove_emoji(author).strip()
            if len(author) > 1:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.get('verified_buyer')
        if is_verified is True:
            review.add_property(type='is_verified_buyer', value=is_verified)

        hlp_yes = rev.get('thumb_up')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('thumb_down')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.get('title')
        excerpt_html = rev.get('body_html')
        excerpt = data.parse_fragment(excerpt_html).xpath('.//text()').string(multiple=True)
        if excerpt and len(remove_emoji(excerpt).replace('\n', '').replace('\r', '').strip()) > 2:
            if title:
                review.title = remove_emoji(title).strip()
        else:
            excerpt = title

        if excerpt:
            if '{"number_of_reviews"' in excerpt:
                excerpt = excerpt_html

            excerpt = remove_emoji(excerpt).replace('\n', '').replace('\r', '').replace('<p>', '').replace('</p>', '').replace('<a>', '').replace('</a>', '').strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 10
    if offset < context['revs_cnt']:
        next_page = context.get("page", 1) + 1
        next_url = "https://judge.me/reviews/reviews_for_widget?url=milex-south-africa.myshopify.com&shop_domain=milex-south-africa.myshopify.com&platform=shopify&page={page}&per_page=10&product_id={ssid}".format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url, max_age=0, force_charset='utf-8'), process_reviews, dict(context, product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
