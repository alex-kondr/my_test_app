from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Shop all', 'Choose your hair goal']


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
    session.queue(Request("https://denmanbrushus.com/", force_charset="utf-8"), process_frontpage, dict(cat='Hairbrushes'))


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@class="mega-menu__list"]/li/div/a')
    for cat in cats:
        url = cat.xpath('@href').string()
        name = cat.xpath('text()').string()
        if name not in XCAT:
            session.queue(Request(url, force_charset="utf-8"), process_prodlist, dict(cat=context['cat'] + '|' + name))


def process_prodlist(data, context, session):
    prods_json = data.xpath('''//script[contains(., "collectionAllProducts")]/text()''').string()
    if not prods_json:
        return

    prods_json = prods_json.split('collectionAllProducts = ', 1)[-1].split('}];')[0] + '}]'
    prods = simplejson.loads(prods_json)
    for prod in prods:
        name = prod.get('title')
        url = 'https://denmanbrushus.com/collections/detangle/products/' + prod.get('handle', '')
        ssid = prod.get('id')
        session.queue(Request(url, force_charset="utf-8"), process_product, dict(context, name=name, url=url, ssid=ssid))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.ssid = str(context['ssid'])
    product.manufacturer = 'Denman'

    try:
        prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type": "Product"')]//text()''').string())

        mpn = prod_json.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('offers', [{}])[0].get('gtin12')
        if ean:
            product.add_property(type='id.ean', value=ean)
    except:
        pass

    pid = data.xpath('//div[@class="ruk_rating_snippet"]/@data-sku').string()

    if pid:
        revs_url = 'https://api.reviews.co.uk/product/review?store=www.denmanbrush.com&sku=' + pid + '&mpn=&lookup=&product_group=&minRating=1&tag=&sort=undefined&per_page=10&page=1'
        session.do(Request(revs_url, force_charset='utf-8'), process_reviews, dict(product=product, pid=pid))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('reviews', {}).get('data', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev['product_review_id'])
        review.title = rev.get('title')

        date = rev.get('date_created')
        if date:
            review.date = date.split()[0]

        first_name = rev.get('reviewer', {}).get('first_name') or ''
        last_name = rev.get('reviewer', {}).get('last_name') or ''
        author = first_name + ' ' + last_name
        if author.strip():
            author = author.strip()
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.get('reviewer', {}).get('verified_buyer')
        if is_verified and is_verified == "yes":
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.get('review')
        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').replace('\r', '').strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = context.get('revs_cnt', revs_json.get('stats', {}).get('count'))
    offset = context.get('offset', 0) + 10
    if revs_cnt and int(revs_cnt) > offset:
        next_page = context.get('page', 1) + 1
        next_url = 'https://api.reviews.co.uk/product/review?store=www.denmanbrush.com&sku=' + context['pid'] + '&mpn=&lookup=&product_group=&minRating=1&tag=&sort=undefined&per_page=10&page=' + str(next_page)
        session.do(Request(next_url, force_charset='utf-8'), process_reviews, dict(context, product=product, revs_cnt=revs_cnt, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
