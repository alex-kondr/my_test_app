from agent import *
from models.products import *
import simplejson


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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.weleda.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(@class, "product-category")]/a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="product-teaser__content"]')
    for prod in prods:
        name = prod.xpath('a/h2/text()').string()
        url = prod.xpath('a/@href').string().split('?')[0]

        revs_cnt = prod.xpath('.//div[@class="rating__info"]/div[@class]/text()').string()
        if revs_cnt:
            revs_cnt = int(revs_cnt.strip('( )'))
            if revs_cnt > 0:
                session.queue(Request(url), process_product, dict(context, name=name, url=url, revs_cnt=revs_cnt))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = 'Weleda'

    options = """--compressed -H 'Accept-Encoding: deflate' -H 'x-channel: deu-de' -H 'Cookie: CUSTOMER_UUID=c6fdd1f3-cd68-4778-b6b8-5b23243a2b16; OptanonConsent=isGpcEnabled=0&datestamp=Wed+Aug+27+2025+11%3A40%3A06+GMT%2B0300+(%D0%B7%D0%B0+%D1%81%D1%85%D1%96%D0%B4%D0%BD%D0%BE%D1%94%D0%B2%D1%80%D0%BE%D0%BF%D0%B5%D0%B9%D1%81%D1%8C%D0%BA%D0%B8%D0%BC+%D0%BB%D1%96%D1%82%D0%BD%D1%96%D0%BC+%D1%87%D0%B0%D1%81%D0%BE%D0%BC)&version=202407.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=dc2446c2-d08b-47ec-8c65-49efbb7c1469&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0004%3A1%2CC0002%3A1%2CC0007%3A1&intType=1&geolocation=UA%3B51&AwaitingReconsent=false; OptanonAlertBoxClosed=2025-08-27T07:44:54.487Z; SERVERID=858c910bbe24642d9518a44a039f053f|b0fb2f40b9f9ed2a9935743ec69c9e2a'"""
    revs_url = 'https://www.weleda.de/restapi/review/abstract-product?sku={}&page=0&ipp=3&sort-by=best'.format(product.sku)
    session.do(Request(revs_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(context, product=product))


def process_reviews(data, context, session):
    product = context['product']

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        author = rev.get('author')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('verified')
        if is_verified_buyer is True:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('summary')
        excerpt = rev.get('description')
        if excerpt and len(excerpt.replace('\n', '').replace('\r', '').replace('\t', '').strip()) > 2:
            review.title = title
        else:
            excerpt = title

        if excerpt and '(Ursprünglich erschienen auf influenster.com)' not in excerpt:
            excerpt = excerpt.replace('\n', '').replace('\r', '').replace('\t', '').strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 3
    if offset < context['revs_cnt']:
        options = """--compressed -H 'Accept-Encoding: deflate' -H 'x-channel: deu-de' -H 'Cookie: CUSTOMER_UUID=c6fdd1f3-cd68-4778-b6b8-5b23243a2b16; OptanonConsent=isGpcEnabled=0&datestamp=Wed+Aug+27+2025+11%3A40%3A06+GMT%2B0300+(%D0%B7%D0%B0+%D1%81%D1%85%D1%96%D0%B4%D0%BD%D0%BE%D1%94%D0%B2%D1%80%D0%BE%D0%BF%D0%B5%D0%B9%D1%81%D1%8C%D0%BA%D0%B8%D0%BC+%D0%BB%D1%96%D1%82%D0%BD%D1%96%D0%BC+%D1%87%D0%B0%D1%81%D0%BE%D0%BC)&version=202407.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=dc2446c2-d08b-47ec-8c65-49efbb7c1469&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0004%3A1%2CC0002%3A1%2CC0007%3A1&intType=1&geolocation=UA%3B51&AwaitingReconsent=false; OptanonAlertBoxClosed=2025-08-27T07:44:54.487Z; SERVERID=858c910bbe24642d9518a44a039f053f|b0fb2f40b9f9ed2a9935743ec69c9e2a'"""
        revs_url = 'https://www.weleda.de/restapi/review/abstract-product?sku={sku}&page={offset}&ipp=3&sort-by=best'.format(sku=product.sku, offset=offset)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(context, product=product, offset=offset))

    elif product.reviews:
        session.emit(product)
