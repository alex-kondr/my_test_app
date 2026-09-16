from agent import *
from models.products import *
import simplejson
import re


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) Gecko/20100101 Firefox/155.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Cookie: _cmuid=3ff6b2d2-b315-4f62-86c9-40374c6c3c84; datadome=4RBTS3MtIQqLlBO3gf6tsAUO8Dmmf0Im6pzpNTXvc61q_QA36s1yNBap6NV~71oFt6qHwHS8LjK9estCOdxKhA8oW3GLhM5U8dN0QZHREevQAHXL2ZF4G2YdCecWHgP2; wdctx=v5.epeMhH8v3iivLMV5o2GKwf-ILh9Azxv4WuadMSDvyrxV5SUckONyo7RcNMkmGv1QiXfgm2GtSbfoVj1moV3bpZO5FzT9Q55mstxQL2cL1p7hQahqG206bz7BUBpeLFtxnuToSXRS1WjfXD5TyfkZed_gT163SNUiN6PxFU2xJfo4qdAKCsytc8tQoOXLhTs5BCapvJHMpR_zdQESx5dphCP4iM-TNFJ0vrw4SeqBGczG.bGO5NOROR-eAZbK6m1HhUg.y_BsfTBc1bI; OptOutOnRequest=groups=googleAnalytics:1,googleAdvertisingProducts:1,tikTok:1,allegroAdsNetwork:1,facebook:1,rtbHouse:1,rasp:1,pinterest:1; gdpr_permission_given=1; _meta_googleGtag_settings=4e5a45d52f17bc4e567bbe2aaafea8a73d012998; _meta_googleGtag_session_id=1789565762; _meta_googleGtag_ga_session_count=1; _meta_googleGtag_ga=GA1.2.1883932283.1789565762; _meta_googleGtag_ga_library_loaded=1789566350068; g_state={"i_l":2,"i_ll":1789566350031,"i_b":"2fTPruJCHZda8n7fyI07QcRilOwBBK2qse/c7RDfpXA","i_e":{"enable_itp_optimization":24},"i_et":1789566350031,"i_p":1789652166136}; _fbp=fb.1.1789565931481.792485742; _meta_facebookTag_sync=1789565931481; _ttp=J_wp3sxF7ofCYxC6fnsSVQ_vxAl; _meta_urlParameters_utm_source=mall.cz; _meta_urlParameters_utm_source_30=mall.cz; _meta_urlParameters_utm_source_30_timestamp=1789566350056; _meta_rtbHouse_settings=3dda4a52a350b6c1012f65a65e347d9115a6c925'"""


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


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://allegro.cz/obchod/mall-cz?utm_source=mall.cz&dd_referrer=', use='curl', force_charset='utf-8', options=OPTIONS), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class="grid-cell"]/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath("@href").string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_category, dict(cat=name))


def process_category(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="category-products"]/div')
    for prod in prods:
        name = prod.xpath('a/span[@class="pbcr__title"]/text()').string()
        url = prod.xpath("a/@href").string()
        ssid = prod.xpath('@id').string()

        revs_cnt = prod.xpath('.//span[@data-testid="rating-count"]/text()').string()
        if revs_cnt:
            revs_cnt = revs_cnt.strip(' x')
            if int(revs_cnt) > 0:
                session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url, ssid=ssid))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_category, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)
    
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.manufacturer = data.xpath('//div[@itemprop="brand"]/meta/@content').string()
    product.category = context['cat']
    product.ssid = context['ssid']
    product.sku = product.ssid

    ean = data.xpath('''//script[contains(., '"gtin12":"')]/text()''').string()
    if ean:
        ean = ean.split('"gtin12":"')[-1].split('"', 1)[0]
        product.properties.append(ProductProperty(type='id.ean', value=ean))

    options = r"""--compressed -X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br' -H 'content-type: application/json' -H 'x-shop-id: CZ10MA' -H 'x-is-bot: 0' -H 'Connection: keep-alive' --data-raw '{"operationName":"getReviewForDetail","variables":{"limit":10000,"offset":0,"productId":"{}"},"query":"query getReviewForDetail($productId: ID!, $offset: Int!, $limit: Int!, $filter: GetReviewFilter) {\n  reviewsData: getProductReviews(\n    productId: $productId\n    pagination: {offset: $offset, limit: $limit}\n    filter: $filter\n    sort: [{field: \"usefulness\", order: desc}, {field: \"created_at\", order: desc}]\n  ) {\n    items {\n      id\n      user\n      rank\n      message\n      source\n      showAuthor\n      createdAt\n      pros\n      cons\n      medias {\n        id\n        __typename\n      }\n      usefulness {\n        positiveCount\n        negativeCount\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  negativeReviews: getProductReviews(\n    filter: {rankFrom: 1, rankTo: 3}\n    productId: $productId\n  ) {\n    hits\n    __typename\n  }\n  positiveReviews: getProductReviews(\n    filter: {rankFrom: 4, rankTo: 5}\n    productId: $productId\n  ) {\n    hits\n    __typename\n  }\n}\n"}'""".format(product.ssid)
    session.do(Request('https://www.mall.cz/web-gateway/graphql', use='curl', options=options, force_charset='utf-8', max_age=0), process_reviews, dict(product=product))

    if product.reviews:
        session.emit(product)


def process_reviews(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)
    
    product = context['product']
    resp = simplejson.loads(data.content)

    revs = resp.get('data', {}).get('reviewsData', {}).get('items', [])
    for rev in revs:
        if rev.get('source') != 'mall':
            continue

        review = Review()
        review.ssid = rev['id']
        review.type = 'user'
        review.url = product.url

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('user')
        if author:
            author = remove_emoji(author).strip()
            if author:
                review.authors.append(Person(name=author, ssid=author))

        hlp_yes = rev.get('usefulness', {}).get('positiveCount')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('usefulness', {}).get('negativeCount')
        if hlp_no:
            review.add_property(type='helpful_votes', value=int(hlp_no))

        grade = rev.get('rank')
        if grade:
            review.grades.append(Grade(type='overall', value=float(grade), best=5.0))

        pros = rev.get('pros')
        for pro in pros:
            review.properties.append(ReviewProperty(type='pros', value=pro))

        cons = rev.get('cons')
        for con in cons:
            review.properties.append(ReviewProperty(type='cons', value=con))

        excerpt = rev.get('message')
        if excerpt:
            excerpt = remove_emoji(excerpt).strip()
            if excerpt:
                review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
                product.reviews.append(review)