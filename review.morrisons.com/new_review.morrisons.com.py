from agent import *
from models.products import *
import simplejson


XCAT = ["Meat & Fish", "Fruit & Veg", "Fresh", "Bakery & Cakes", "Food Cupboard", "Frozen", "Drinks", "Beer, Wines & Spirits", "World Foods", "Free From", "Adult Cat Food (1-6 years)", "Senior Cat Food (7 years+)", "Kitten Food (0-1 years)", "Cat Treats & Milk", "Adult Dog Food (2 years+)", "Senior Dog Food (7 years+)", "Puppy Food (0-2 years)", "Small Breed Dog Food", "Dog Treats, Chews & Biscuits", "Butchers", "Pet Bigger Packs", "Treats", "Advanced Nutrition", "Christmas for Pets", "Advertised Brand", "Baby Milk", "Baby & Toddler Meals & Drinks", "Finger Foods", "HiPP Organic", "New"]


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
    session.queue(Request("https://groceries.morrisons.com/categories"), process_catlist, dict())


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
            session.queue(Request(url), process_catlist, dict(cat=context.get('cat', '')+'|'+name, url=url))


def process_category(data, context, session):
    strip_namespace(data)

    data_json = data.xpath('//script[@data-test="initial-state-script"]/text()').string()
    if data_json:
        prods_id = []

        productGroups = simplejson.loads(data_json.replace('window.__INITIAL_STATE__=', '')).get('data', {}).get('products', {}).get('catalogue', {}).get('data', {}).get('productGroups', [])
        for prod in productGroups:
            prods_id += prod.get('products')

        options = """--compressed -X PUT -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0' -H 'Accept: application/json; charset=utf-8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Referer: https://groceries.morrisons.com/categories/fruit-veg-flowers/salads/176758' -H 'X-CSRF-TOKEN: 759c5112-f2da-4aea-8777-16f0f1710891' -H 'client-route-id: 1c59073c-c97c-4cb8-87ef-91cb68333d36' -H 'ecom-request-source: web' -H 'ecom-request-source-version: 2.0.0-2026-02-11-12h15m51s-e1c187d9' -H 'page-view-id: 1cf06ccf-1eed-4ee4-b153-6a56a5de47ce' -H 'content-type: application/json; charset=utf-8' -H 'Origin: https://groceries.morrisons.com' -H 'Connection: keep-alive' -H 'Cookie: VISITORID=_T6QhWcVbfq7c3RLfFLS_zkw6HrfyBOYwa_50brXyAo8u9vxFa2GCLddWn_1H_DxA186JbdkIxDYH2U2TkwWu7vF37-ibZiX6Lk2Ag==; AWSALB=2PE5UAWpWKqrm2f4JZsfAidJSiw5UB1DuL0VOkg9fqbUAJr048egFN3JC0eJSDMALH7amNpNphWVgi5p9T8F9FcgTO8pRQxopWGZVQjO6ZHFcJ0K45fnfwkv8WqS; AWSALBCORS=2PE5UAWpWKqrm2f4JZsfAidJSiw5UB1DuL0VOkg9fqbUAJr048egFN3JC0eJSDMALH7amNpNphWVgi5p9T8F9FcgTO8pRQxopWGZVQjO6ZHFcJ0K45fnfwkv8WqS; global_sid=edrUvETOxLW6Uws05AoK8hhBPY87tZ9ahxL3O6qaRiZG4WCejcjReyBynEG4A2gl8AUNl9Kx97P9DdHYdXamsIcfPkOZIf3szVeljg==; OptanonConsent=isGpcEnabled=0&datestamp=Thu+Feb+12+2026+14%3A07%3A21+GMT%2B0200+(%D0%B7%D0%B0+%D1%81%D1%85%D1%96%D0%B4%D0%BD%D0%BE%D1%94%D0%B2%D1%80%D0%BE%D0%BF%D0%B5%D0%B9%D1%81%D1%8C%D0%BA%D0%B8%D0%BC+%D1%81%D1%82%D0%B0%D0%BD%D0%B4%D0%B0%D1%80%D1%82%D0%BD%D0%B8%D0%BC+%D1%87%D0%B0%D1%81%D0%BE%D0%BC)&version=202501.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=b62cbd90-562e-4eed-9135-28b58cf73009&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0003%3A1%2CC0004%3A1%2CC0002%3A1&intType=1&geolocation=UA%3B51&AwaitingReconsent=false; OptanonAlertBoxClosed=2026-02-12T11:31:20.829Z; contentExperienceUserId=6a904135-7147-4fbc-a6f7-5016b18a522e; language=en-GB; AWSALBTG=vrNDN2IuGroSs53kZLEBKmVZFh4XmLJYaYU7eiDh3KugCudMSFnkIudKi/va3IQ+Lu/IxpS0f+DsgHE3XZwEjyepcjjUigHosxnX7+z0QuNThMX/JshWahDq4FNesN4wEKFhFxuZ7BurhukL7ZEwvfVfGYH8Po6pzwxVgEWijC7v; AWSALBTGCORS=vrNDN2IuGroSs53kZLEBKmVZFh4XmLJYaYU7eiDh3KugCudMSFnkIudKi/va3IQ+Lu/IxpS0f+DsgHE3XZwEjyepcjjUigHosxnX7+z0QuNThMX/JshWahDq4FNesN4wEKFhFxuZ7BurhukL7ZEwvfVfGYH8Po6pzwxVgEWijC7v' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'Priority: u=4' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' --data-raw '{}'""".format(str(prods_id).replace("u'", '"').replace("'", '"'))
        url = 'https://groceries.morrisons.com/api/webproductpagews/v6/products'
        session.queue(Request(url, use='curl', options=options, max_age=0), process_prodlist, dict(context))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = simplejson.loads(data.content).get('products')
    for prod in prods:
        product = Product()
        product.name = prod.get('name')
        product.ssid = prod.get('productId')
        product.sku = str(prod.get('retailerProductId'))
        product.category = context['cat']
        product.manufacturer = prod.get('brand')
        product.url = 'https://groceries.morrisons.com/products/' + product.ssid

        revs_cnt = prod.get('ratingSummary', {}).get('count')
        if revs_cnt and int(revs_cnt) > 0:
            revs_url = 'https://groceries.morrisons.com/api/ecomreviews/v1/products/{}/reviews'.format(product.ssid)
            session.do(Request(revs_url), process_reviews, dict(product=product))

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
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    next_page = revs_json.get('metadata', {}).get('nextPage')
    if next_page:
        next_url = 'https://groceries.morrisons.com/api/ecomreviews/v1/products/{ssid}/reviews?nextPage={page}'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
