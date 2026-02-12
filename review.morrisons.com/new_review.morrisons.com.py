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
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request("https://groceries.morrisons.com/categories"), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(@class, "list__item")]/a[@data-test="root-category-link"]')
    if not cats:
        process_prodlist(data, context, session)
        return

    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()

        if name not in XCAT:
            session.queue(Request(url), process_catlist, dict(cat=context.get('cat', '')+'|'+name, url=url))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "product-card-container")]')
    for prod in prods:
        name = prod.xpath('.//h3/text()').string()
        url = prod.xpath('.//a[contains(@class, "product-link")]/@href').string()

        revs_cnt = prod.xpath('.//div[@data-test="rating-badge"]/text()').string(multiple=True)
        if revs_cnt and int(revs_cnt.strip('( )')) > 0:
            
            print name, url
            # session.queue(Request(url), process_product, dict(context, name=name, url=url))

    options = """--compressed -X PUT -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0' -H 'Accept: application/json; charset=utf-8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Referer: https://groceries.morrisons.com/categories/fruit-veg-flowers/salads/176758' -H 'X-CSRF-TOKEN: 759c5112-f2da-4aea-8777-16f0f1710891' -H 'client-route-id: 1c59073c-c97c-4cb8-87ef-91cb68333d36' -H 'ecom-request-source: web' -H 'ecom-request-source-version: 2.0.0-2026-02-11-12h15m51s-e1c187d9' -H 'page-view-id: 1cf06ccf-1eed-4ee4-b153-6a56a5de47ce' -H 'content-type: application/json; charset=utf-8' -H 'Origin: https://groceries.morrisons.com' -H 'Connection: keep-alive' -H 'Cookie: VISITORID=_T6QhWcVbfq7c3RLfFLS_zkw6HrfyBOYwa_50brXyAo8u9vxFa2GCLddWn_1H_DxA186JbdkIxDYH2U2TkwWu7vF37-ibZiX6Lk2Ag==; AWSALB=2PE5UAWpWKqrm2f4JZsfAidJSiw5UB1DuL0VOkg9fqbUAJr048egFN3JC0eJSDMALH7amNpNphWVgi5p9T8F9FcgTO8pRQxopWGZVQjO6ZHFcJ0K45fnfwkv8WqS; AWSALBCORS=2PE5UAWpWKqrm2f4JZsfAidJSiw5UB1DuL0VOkg9fqbUAJr048egFN3JC0eJSDMALH7amNpNphWVgi5p9T8F9FcgTO8pRQxopWGZVQjO6ZHFcJ0K45fnfwkv8WqS; global_sid=edrUvETOxLW6Uws05AoK8hhBPY87tZ9ahxL3O6qaRiZG4WCejcjReyBynEG4A2gl8AUNl9Kx97P9DdHYdXamsIcfPkOZIf3szVeljg==; OptanonConsent=isGpcEnabled=0&datestamp=Thu+Feb+12+2026+14%3A07%3A21+GMT%2B0200+(%D0%B7%D0%B0+%D1%81%D1%85%D1%96%D0%B4%D0%BD%D0%BE%D1%94%D0%B2%D1%80%D0%BE%D0%BF%D0%B5%D0%B9%D1%81%D1%8C%D0%BA%D0%B8%D0%BC+%D1%81%D1%82%D0%B0%D0%BD%D0%B4%D0%B0%D1%80%D1%82%D0%BD%D0%B8%D0%BC+%D1%87%D0%B0%D1%81%D0%BE%D0%BC)&version=202501.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=b62cbd90-562e-4eed-9135-28b58cf73009&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0003%3A1%2CC0004%3A1%2CC0002%3A1&intType=1&geolocation=UA%3B51&AwaitingReconsent=false; OptanonAlertBoxClosed=2026-02-12T11:31:20.829Z; contentExperienceUserId=6a904135-7147-4fbc-a6f7-5016b18a522e; language=en-GB; AWSALBTG=vrNDN2IuGroSs53kZLEBKmVZFh4XmLJYaYU7eiDh3KugCudMSFnkIudKi/va3IQ+Lu/IxpS0f+DsgHE3XZwEjyepcjjUigHosxnX7+z0QuNThMX/JshWahDq4FNesN4wEKFhFxuZ7BurhukL7ZEwvfVfGYH8Po6pzwxVgEWijC7v; AWSALBTGCORS=vrNDN2IuGroSs53kZLEBKmVZFh4XmLJYaYU7eiDh3KugCudMSFnkIudKi/va3IQ+Lu/IxpS0f+DsgHE3XZwEjyepcjjUigHosxnX7+z0QuNThMX/JshWahDq4FNesN4wEKFhFxuZ7BurhukL7ZEwvfVfGYH8Po6pzwxVgEWijC7v' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'Priority: u=4' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' --data-raw '["0ee010d9-6036-43a1-98cb-c96b32da7511","509195de-2b88-4d6a-9cb1-751ab381fe67","a540a510-2361-420d-b890-ba392db2c301","1f1001aa-3fc1-4498-94eb-2bc369caaf94","ed1ddd5d-c14c-4bbe-b329-487460f050f5","f0c2e685-a299-4ece-8671-cb7892476706","9b0a0be8-0688-4130-bd72-05b670b3c8f0","0e8ce559-d233-4d0e-99a5-029d3deca407","748873b9-3b4a-49df-89ad-8904ba8a7555","68c5e714-d294-4252-9a82-5d49694dcc83","ed12812c-25d7-449a-b480-ed25bf111e4f","375f330a-e060-4b68-9eac-925ea8f0f4f0","515247c9-11fc-4b18-b626-827151d5a927","96be4578-b73b-4c3a-bd1d-a24b0f8c9a77","71e835d2-676b-40fa-a22c-d046ea18caea","5677dec4-4684-43d7-aeed-fbfb73a6cf03","80a12375-070e-4dda-ab9e-d649ae1392ec","de22ff97-0637-4b60-b980-05b55839d4fc","b6f69dd6-64d5-4f40-9074-cc43bc95de76","917bb3a4-627d-49d6-84a2-fef22211d156","5d93438e-3f92-41ce-ad98-206c55f31e87","dfa109d9-8d97-4c12-9f2f-bae5a1b8dfb2","9edfd16a-1ac3-4126-b654-0e878e93dc82","f374a182-bc3b-43c9-a77f-4a5a5854a41c"]'"""
    next_url


def process_review(data, context, session):
    strip_namespace(data)

    try:
        resp = simplejson.loads(data.content)
    except:
        resp = simplejson.loads(data.content.split("\r\n")[-1])

    revs_total = int(resp.get("totalCount"))
    revs = context.get("revs", [])
    revs += resp.get("reviews")

    if not revs:
        return

    if revs_total > len(revs):
        revs_url = "https://groceries.morrisons.com/webshop/api/v1/products/" + context["sku"] + "/reviews?sortOrder=MOST_RECENT&limit=100&offset=" + str(len(revs))
        session.queue(Request(revs_url, use="curl"), process_review, dict(context, revs=revs))
    else:
        product = Product()
        product.name = context["name"]
        product.url = context["url"]
        product.ssid = context["url"].split("/")[-1]
        product.sku = context["sku"]
        product.category = context["cat"]
        product.manufacturer = context["manufacturer"]

        for rev in revs:
            review = Review()
            review.type = "user"
            review.title = rev.get("title")
            review.ssid = str(rev.get("reviewId"))
            review.date = rev.get("creationDate")
            review.url = product.url

            author = rev.get("customerNickname")
            author_ssid = rev.get("customerNumber")
            author_url = "https://groceries.morrisons.com/webshop/readAllCustomerReviews.do?cn=" + author_ssid
            review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))

            grade = rev.get("rating")
            if grade:
                review.grades.append(Grade(type="overall", value=float(grade), worst=0.0, best=5.0))

            excerpt = rev.get("text")
            if excerpt:
                review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
                product.reviews.append(review)

        if product.reviews:
            session.emit(product)
