from agent import *
from models.products import *
import simplejson
import re


TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7InJvbGUiOiJndWVzdCIsImN1c3RvbWVySWQiOm51bGwsInNob3BpZnlDdXN0b21lcklkIjpudWxsLCJzZXNzaW9uVG9rZW4iOiIzZWU1ODRjNDgzNmQ1NTU1OWMyYzVhZGEiLCJzaG9wSWQiOjEzNTI5MX0sImV4cCI6MTczODA1NTQ4MywiaWF0IjoxNzM4MDUxODgzfQ.qW1v6e0tReDR52Wr3yK2aXfLh5pXC6dQWYaGa-jogCM'


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
    session.queue(Request("https://store.blackview.hk"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@data-placement="bottom"]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl'), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//h3[@class="t4s-product-title"]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    prod_json = data.xpath('//script[contains(., "@id")]//text()').string()
    if not prod_json:
        return

    prod_json = simplejson.loads(prod_json.replace('\\', '/'))

    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.ssid = data.xpath('//div/@data-product_id').string()
    product.manufacturer = 'Blackview'

    mpn = prod_json.get("sku")
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = prod_json.get("mpn")
    if ean:
        product.add_property(type='id.ean', value=str(ean))

    revs_cnt = prod_json.get("aggregateRating", {}).get("reviewCount")
    if revs_cnt and int(revs_cnt) > 0:
        revs_url = "https://store.blackview.hk/apps/ssw/storefront-api/reviews-storefront/v2/review/getReviewList?x-gw-current-app=default&designMode=false&productId={ssid}&sortingOptions%5B%5D=mostRecent&perPage=5&token={token}&x-gw-token-strategy=growave".format(ssid=product.ssid, token=TOKEN)
        session.do(Request(revs_url, use='curl', max_age=0, force_charset='utf-8'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('items', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        first_name = rev.get('customer', {}).get('firstName') or ''
        last_name = rev.get('customer', {}).get('lastName') or ''
        author = (first_name + ' ' + last_name).strip()
        author_ssid = rev.get('customer', {}).get('id')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=str(author_ssid)))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall and grade_overall > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.get('customer', {}).get('verifiedBuyer')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        helpful = rev.get('votes')
        if helpful and helpful > 0:
            review.add_property(type='helpful_votes', value=helpful)

        title = rev.get('title')
        excerpt = rev.get('body')
        if excerpt and len(remove_emoji(excerpt).strip(' +-.\n\t')) > 1:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip(' +-.\n\t')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    revs_cnt = revs_json.get('totalCount')
    if offset < revs_cnt:
        revs_url = "https://store.blackview.hk/apps/ssw/storefront-api/reviews-storefront/v2/review/getReviewList?x-gw-current-app=default&designMode=false&productId={ssid}&offset={offset}&perPage=5&sortingOptions%5B%5D=mostRecent&token={token}&x-gw-token-strategy=growave".format(ssid=product.ssid, offset=offset, token=TOKEN)
        session.do(Request(revs_url, use='curl', max_age=0, force_charset='utf-8'), process_reviews, dict(context, product=product, offset=offset))

    elif product.reviews:
        session.emit(product)
