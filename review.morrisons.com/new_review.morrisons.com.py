from agent import *
from models.products import *
import simplejson
import HTMLParser


XCAT = ["Meat & Fish", "Fruit & Veg", "Fresh", "Bakery & Cakes", "Food Cupboard", "Frozen", "Drinks", "Beer, Wines & Spirits", "World Foods", "Free From", "Adult Cat Food (1-6 years)", "Senior Cat Food (7 years+)", "Kitten Food (0-1 years)", "Cat Treats & Milk", "Adult Dog Food (2 years+)", "Senior Dog Food (7 years+)", "Puppy Food (0-2 years)", "Small Breed Dog Food", "Dog Treats, Chews & Biscuits", "Butchers", "Pet Bigger Packs", "Treats", "Advanced Nutrition", "Christmas for Pets", "Advertised Brand", "Baby Milk", "Baby & Toddler Meals & Drinks", "Finger Foods", "HiPP Organic", "New"]
h = HTMLParser.HTMLParser()

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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://groceries.morrisons.com/categories", force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(@class, "list__item")]/a[@data-test="root-category-link"]')
    if not cats:
        process_category(data, context, session)
        return

    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()

        if name not in XCAT:
            session.queue(Request(url, force_charset='utf-8'), process_catlist, dict(cat=context.get('cat', '')+'|'+name))


def process_category(data, context, session):
    strip_namespace(data)

    data_json = data.xpath('//script[@data-test="initial-state-script"]/text()').string()
    if data_json:
        prods_id = []

        data_json = simplejson.loads(data_json.replace('window.__INITIAL_STATE__=', ''))
        productGroups = data_json.get('data', {}).get('products', {}).get('catalogue', {}).get('data', {}).get('productGroups', [])
        for prod in productGroups:
            prods_id += prod.get('products')

        options = """--compressed -X PUT -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0' -H 'Accept: application/json; charset=utf-8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Referer: https://groceries.morrisons.com/categories' -H 'X-CSRF-TOKEN: 6e03c497-e251-4021-a17f-af5709589dd7' -H 'client-route-id: d481d19c-e6e4-4aa0-afbc-97fdb3c8da10' -H 'ecom-request-source: web' -H 'ecom-request-source-version: 2.0.0-2026-02-12-09h03m25s-aa743fa3' -H 'page-view-id: 9367652e-b59d-487d-a2be-b7bc5dd37ee3' -H 'content-type: application/json; charset=utf-8' -H 'Origin: https://groceries.morrisons.com' -H 'Connection: keep-alive' -H 'Cookie: VISITORID=P5jKof6l6SXKlqtZz0QVVkKau2DK1dOJfbD-6Iy518b5OCO4y1W3_v5YKa7qxg9IgmhCEY0m7YoKbaOE_pwCfThGPbXAYDu25wlDtw==; AWSALB=hJy+bGmbATS6saTWfr5NaGWIy0vntPp8iIQbPvZBd0xTrfshGxfbV9Rws81XaZjUr5p2XCYUt1+ABEF4w9AWrELMXxJ49TTxSVx7MYS6DUM0Lv2gQyc6U7ITFmNH; AWSALBCORS=hJy+bGmbATS6saTWfr5NaGWIy0vntPp8iIQbPvZBd0xTrfshGxfbV9Rws81XaZjUr5p2XCYUt1+ABEF4w9AWrELMXxJ49TTxSVx7MYS6DUM0Lv2gQyc6U7ITFmNH; global_sid=ubBCMpF5xjQhIdR-7XQAhm-MszQFoSlKhwSz4pUVsu-0jTlc1fdUzLxIUGzESQlLcejsldv2dJG1yRIoF5Nbe11Fx76zUpsIrsvROw==; OptanonConsent=isGpcEnabled=0&datestamp=Fri+Feb+13+2026+13%3A03%3A13+GMT%2B0200+(%D0%B7%D0%B0+%D1%81%D1%85%D1%96%D0%B4%D0%BD%D0%BE%D1%94%D0%B2%D1%80%D0%BE%D0%BF%D0%B5%D0%B9%D1%81%D1%8C%D0%BA%D0%B8%D0%BC+%D1%81%D1%82%D0%B0%D0%BD%D0%B4%D0%B0%D1%80%D1%82%D0%BD%D0%B8%D0%BC+%D1%87%D0%B0%D1%81%D0%BE%D0%BC)&version=202501.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=9e5b6786-5ba3-4d52-94c8-f00355089f13&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0003%3A1%2CC0004%3A1%2CC0002%3A1&intType=1; OptanonAlertBoxClosed=2026-02-13T11:03:13.045Z; contentExperienceUserId=58a2d1a1-b232-48e3-9d8a-9c7cb4295689; language=en-GB' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'Priority: u=4' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers' --data-raw '{prods_id}'""".format(prods_id=str(prods_id).replace("u'", '"').replace("'", '"'))
        url = 'https://groceries.morrisons.com/api/webproductpagews/v6/products'
        session.do(Request(url, use='curl', options=options, max_age=0, force_charset='utf-8'), process_prodlist, dict(context, prods_cnt=len(prods_id), cat_url=data.response_url))


def process_prodlist(data, context, session):
    strip_namespace(data)

    try:
        prods = simplejson.loads(data.content).get('products')
    except:
        return

    for prod in prods:
        product = Product()
        product.name = prod.get('name')
        product.ssid = prod.get('productId')
        product.sku = str(prod.get('retailerProductId'))
        product.category = context['cat'].strip(' |')
        product.manufacturer = prod.get('brand')
        product.url = 'https://groceries.morrisons.com/products/' + product.sku

        revs_cnt = prod.get('ratingSummary', {}).get('count')
        if revs_cnt and int(revs_cnt) > 0:
            revs_url = 'https://groceries.morrisons.com/api/ecomreviews/v1/products/{}/reviews'.format(product.ssid)
            session.do(Request(revs_url, force_charset='utf-8'), process_reviews, dict(product=product))

# load all prods


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    try:
        revs_json = simplejson.loads(data.content)
    except:
        return

    revs = revs_json.get('reviews', [])
    if not revs:
        return

    for rev in revs:
        if rev.get('locale') != 'en-GB':
            continue

        review = Review()
        review.type = "user"
        review.url = product.url
        review.ssid = str(rev.get("id"))

        date = rev.get("createdDate")
        if date:
            review.date = date.split('T')[0]

        author = rev.get("nickname")
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade = rev.get("rating")
        if grade and float(grade) > 0:
            review.grades.append(Grade(type="overall", value=float(grade), best=5.0))

        is_verified_buyer = rev.get('isVerifiedBuyer')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('helpfulVotes')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        title = rev.get("headline")
        excerpt = rev.get("comments")
        if excerpt and len(h.unescape(excerpt).replace('\n', '').strip()) > 2:
            if title:
                review.title = h.unescape(title).replace('\\x27', "'").replace('\\x26', '').replace('â\\x80¦', '').strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = h.unescape(excerpt).replace('\n', '').replace('\\x27', "'").replace('\\x26', '').replace('â\\x80¦', '').strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    next_page = revs_json.get('metadata', {}).get('nextPage')
    if next_page:
        next_url = 'https://groceries.morrisons.com/api/ecomreviews/v1/products/{ssid}/reviews?nextPage={page}'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url, force_charset='utf-8'), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
