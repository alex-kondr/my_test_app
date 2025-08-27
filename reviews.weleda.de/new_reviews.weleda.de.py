from agent import *
from models.products import *
import simplejson


XCAT = ['Angebote', 'Weleda', 'Magazin']


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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.weleda.de/', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(@class, "main-menu-bar")]')
    for cat in cats:
        name = cat.xpath('span/a//text()').string(multiple=True)

        if name not in XCAT:
            sub_cats = cat.xpath('.//div[@class="single-level-menu-list__entry" and div/span[contains(text(), "Kategorie")]]/a')
            if sub_cats:
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath('.//text()').string(multiple=True)
                    url = sub_cat.xpath('@href').string()
                    session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name + '|' + sub_name))
            else:
                sub_cats = cat.xpath('.//div[@class="single-level-menu-list__entry"]')
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath('div//text()').string(multiple=True)

                    sub_cats1 = sub_cat.xpath('a')
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('.//text()').string(multiple=True)
                        url = sub_cat1.xpath('@href').string()
                        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="product-teaser__content"]')
    for prod in prods:
        name = prod.xpath('a/h2/text()').string()
        url = prod.xpath('a/@href').string().split('?')[0]

        revs_cnt = prod.xpath('.//div[@class="rating__info"]/div[@class]/text()').string()
        if revs_cnt and int(revs_cnt.strip('( )')) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat']
    product.manufacturer = 'Weleda'
    product.sku = product.url.split('-')[-1]

    options = """--compressed -H 'Accept-Encoding: deflate' -H 'x-channel: deu-de' -H 'Cookie: CUSTOMER_UUID=c6fdd1f3-cd68-4778-b6b8-5b23243a2b16; OptanonConsent=isGpcEnabled=0&datestamp=Wed+Aug+27+2025+11%3A40%3A06+GMT%2B0300+(%D0%B7%D0%B0+%D1%81%D1%85%D1%96%D0%B4%D0%BD%D0%BE%D1%94%D0%B2%D1%80%D0%BE%D0%BF%D0%B5%D0%B9%D1%81%D1%8C%D0%BA%D0%B8%D0%BC+%D0%BB%D1%96%D1%82%D0%BD%D1%96%D0%BC+%D1%87%D0%B0%D1%81%D0%BE%D0%BC)&version=202407.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=dc2446c2-d08b-47ec-8c65-49efbb7c1469&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0004%3A1%2CC0002%3A1%2CC0007%3A1&intType=1&geolocation=UA%3B51&AwaitingReconsent=false; OptanonAlertBoxClosed=2025-08-27T07:44:54.487Z; SERVERID=858c910bbe24642d9518a44a039f053f|b0fb2f40b9f9ed2a9935743ec69c9e2a'"""
    revs_url = 'https://www.weleda.de/restapi/review/abstract-product?sku={}&page=0&ipp=3&sort-by=best'.format(product.sku)
    session.do(Request(revs_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(product=product))



def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

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
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('verified')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('summary')
        excerpt = rev.get('description')
        if excerpt and len(excerpt.replace('\n', '').replace('\r', '').replace('\t', '').strip()) > 2:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.replace('\n', '').replace('\r', '').replace('\t', '').strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = revs_json.get('aggregation', {}).get('sumReviews', 0)
    offset = context.get('offset', 0) + 3
    if offset < revs_cnt:
        options = """--compressed -H 'Accept-Encoding: deflate' -H 'x-channel: deu-de' -H 'Cookie: CUSTOMER_UUID=c6fdd1f3-cd68-4778-b6b8-5b23243a2b16; OptanonConsent=isGpcEnabled=0&datestamp=Wed+Aug+27+2025+11%3A40%3A06+GMT%2B0300+(%D0%B7%D0%B0+%D1%81%D1%85%D1%96%D0%B4%D0%BD%D0%BE%D1%94%D0%B2%D1%80%D0%BE%D0%BF%D0%B5%D0%B9%D1%81%D1%8C%D0%BA%D0%B8%D0%BC+%D0%BB%D1%96%D1%82%D0%BD%D1%96%D0%BC+%D1%87%D0%B0%D1%81%D0%BE%D0%BC)&version=202407.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=dc2446c2-d08b-47ec-8c65-49efbb7c1469&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0004%3A1%2CC0002%3A1%2CC0007%3A1&intType=1&geolocation=UA%3B51&AwaitingReconsent=false; OptanonAlertBoxClosed=2025-08-27T07:44:54.487Z; SERVERID=858c910bbe24642d9518a44a039f053f|b0fb2f40b9f9ed2a9935743ec69c9e2a'"""
        revs_url = 'https://www.weleda.de/restapi/review/abstract-product?sku={sku}&page={offset}&ipp=3&sort-by=best'.format(sku=product.sku, offset=offset)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(product=product, offset=offset))

    elif product.reviews:
        session.emit(product)
