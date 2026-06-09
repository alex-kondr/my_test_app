from agent import *
from models.products import *
import simplejson


XCAT = ['All Products', 'About']


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
    session.queue(Request('https://purosound.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[contains(@class, "site-nav site-navigation")]/li')
    for cat in cats:
        name = cat.xpath('a/text()|text()').string(multiple=True)

        if name not in XCAT:
            subcats = cat.xpath('ul/li/a')

            if subcats:
                for subcat in subcats:
                    url = subcat.xpath('@href').string()
                    subcat_name = subcat.xpath('text()').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + subcat_name))

            else:
                url = cat.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="grid-product__content"]')
    for prod in prods:
        link = prod.xpath('a[@class="grid-product__link"]/@href').string().split('/')[-1]
        url = 'https://purosound.com/products/' + link
        name = prod.xpath('.//div[@class="grid-product__title"]//text()').string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//span[@class="klaviyo-star-rating-widget"]/@data-id').string()
    product.sku = product.ssid
    product.category = context['cat']

    try:
        prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type": "Product"')]//text()''').string())
        product.manufacturer = prod_json.get('brand')

        mpn = prod_json.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('gtin12')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)
    except:
        pass

    revs_url = "https://fast.a.klaviyo.com/reviews/api/client_reviews/{ssid}/?product_id={ssid}&company_id=jeKSj7&limit=5&offset=0&sort=0&filter=&type=reviews&media=false".format(ssid=product.ssid)
    session.do(Request(revs_url, max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('reviews', [])
    for rev in revs:

        pid = rev.get('product', {}).get('shopify_id')
        if pid and str(pid) != product.ssid or rev.get('syndication_platform'):
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev['id'])

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('author')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.get('verified')
        if is_verified is True:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('title')
        excerpt = rev.get('content')
        if excerpt and len(remove_emoji(excerpt).replace('\n', '').replace('\r', '')) > 2:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').replace('\r', '').strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = context.get('revs_cnt', revs_json.get('product', {}).get('review_count'))
    offset = context.get('offset', 0) + 5
    if revs_cnt and int(revs_cnt) > offset:
        next_url = "https://fast.a.klaviyo.com/reviews/api/client_reviews/{ssid}/?product_id={ssid}&company_id=jeKSj7&limit=5&offset={offset}&sort=0&filter=&type=reviews&media=false".format(ssid=product.ssid, offset=offset)
        session.do(Request(next_url), process_reviews, dict(product=product, revs_cnt=revs_cnt, offset=offset))

    elif product.reviews:
        session.emit(product)
