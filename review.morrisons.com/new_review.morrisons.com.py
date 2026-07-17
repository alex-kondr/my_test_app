from agent import *
from models.products import *
import simplejson
import HTMLParser
import re


XCAT = ["Meat & Fish", "Fruit & Veg", "Fresh", "Bakery & Cakes", "Food Cupboard", "Frozen", "Drinks", "Beer, Wines & Spirits", "World Foods", "Free From", "Adult Cat Food (1-6 years)", "Senior Cat Food (7 years+)", "Kitten Food (0-1 years)", "Cat Treats & Milk", "Adult Dog Food (2 years+)", "Senior Dog Food (7 years+)", "Puppy Food (0-2 years)", "Small Breed Dog Food", "Dog Treats, Chews & Biscuits", "Butchers", "Pet Bigger Packs", "Treats", "Advanced Nutrition", "Christmas for Pets", "Advertised Brand", "Baby Milk", "Baby & Toddler Meals & Drinks", "Finger Foods", "HiPP Organic", "New"]
h = HTMLParser.HTMLParser()


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
                               u"&#\d+;"  # HTML entities
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


def clean_text(text):
    return h.unescape(remove_emoji(text)).replace('\n', '').replace('\\x27', "'").replace('\\x26', '').replace('â\\x80¦', '').replace(u'â\x80¦', u'').replace('\xe2\x80\x9c', '"').replace('\xe2\x80\x9d', '"').replace(u'\xe2\x80\x9c', '"').replace(u'\xe2\x80\x9d', '"').replace('\\x', "'").replace(u'â\x80\x98', u"'").replace(u'\xe2\x80\x98', u"'").replace(u'Ã\x80', u'À').replace(u'\xc3\x80', u'À').replace(u'\xe2\x98\x86', u'').replace(u'â\x80\x94', u'—').replace(u'Ã\x9c', u'Ü').replace(u'â\x80\x93', u'-').replace(u'Â£', u' ').replace(u' Â', u' ').replace(u'Â\xa0', u' ').replace(u'Â©', u'©').replace(u'Ã¼', u'ü').replace(u'Ã©', u'é').replace(u'Ã¤', u'ä').replace(u'Ã¡', u'á').replace(u'Ã±', u'ñ').strip(u'Â ')


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
    session.queue(Request("https://groceries.morrisons.com/categories", use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(@class, "list__item")]/a[@data-test="root-category-link"]')
    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_category, dict(cat=name))


def process_category(data, context, session):
    strip_namespace(data)

    data_json = data.xpath('//script[@data-test="initial-state-script"]/text()').string()
    if not data_json:
        return

    prods_id = []

    data_json = simplejson.loads(data_json.replace('window.__INITIAL_STATE__=', ''))
    productGroups = data_json.get('data', {}).get('products', {}).get('catalogue', {}).get('data', {}).get('productGroups', [])
    for prod in productGroups:
        prods_id += prod.get('products')

    options = """--compressed -X PUT -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:152.0) Gecko/20100101 Firefox/152.0' -H 'Accept: application/json; charset=utf-8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Referer: https://groceries.morrisons.com/categories' -H 'X-CSRF-TOKEN: ba4bf993-4b8c-48f2-bb32-27cc1548b132' -H 'client-route-id: 35adb31f-bc78-4eb7-96a6-5d635cf29c8b' -H 'ecom-request-source: web' -H 'ecom-request-source-version: 2.0.0-2026-07-16-08h06m50s-7a19b862' -H 'page-view-id: f578d43d-b889-40c5-9ac9-22a5bca5087a' -H 'content-type: application/json; charset=utf-8' -H 'Origin: https://groceries.morrisons.com' -H 'Alt-Used: groceries.morrisons.com' -H 'Connection: keep-alive' -H 'Cookie: VISITORID=cDOI5aRi8uH8kz2vN9HwJUk689eAJn4_fhYTFQtKlaOsZYS3j-yztIPJxZa1_dl-aBbiN6rz_Fg6KnuuMc3oxtu35_7HsSfmbBYGCw==; contentExperienceUserId=8690b9ff-8d83-42bf-bde0-375947bd46f2; language=en-GB; AWSALB=uMhovU0yOUTJCLBLT3zLi+I1gRRxdO+vu5wjboG/Tvhu0TCrWp/awkY1gJ72t0elUXF67jhBJKdQ2e+b2EKqvKX2jXigxRyrqwCw2KaHOtw0OjI6ufKjolkNLVVL; AWSALBCORS=uMhovU0yOUTJCLBLT3zLi+I1gRRxdO+vu5wjboG/Tvhu0TCrWp/awkY1gJ72t0elUXF67jhBJKdQ2e+b2EKqvKX2jXigxRyrqwCw2KaHOtw0OjI6ufKjolkNLVVL; OptanonConsent=isGpcEnabled=0&datestamp=Fri+Jul+17+2026+15%3A07%3A17+GMT%2B0300+(%D0%B7%D0%B0+%D1%81%D1%85%D1%96%D0%B4%D0%BD%D0%BE%D1%94%D0%B2%D1%80%D0%BE%D0%BF%D0%B5%D0%B9%D1%81%D1%8C%D0%BA%D0%B8%D0%BC+%D0%BB%D1%96%D1%82%D0%BD%D1%96%D0%BC+%D1%87%D0%B0%D1%81%D0%BE%D0%BC)&version=202501.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=fd1f1182-bd19-465d-8b20-0e91dc6ec5c7&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0003%3A1%2CC0004%3A1%2CC0002%3A1&intType=1&geolocation=UA%3B51&AwaitingReconsent=false; OptanonAlertBoxClosed=2026-07-14T14:04:59.588Z; AWSALBTG=G9VGYmGnv/4c+dr3wXqGzhAsPaNcV/8SDcKzoaicpnNJkj6mD4t3+96/W6Ok6iEZLmJyCHIpj10fHA2GiQ2q/ldZFvQNxbFCxr+dzuxSB4lfT1QFAkFumFQe6Jv2i8v2OJMXg1e1ZCORnGMZIV3EtuMmTZCKSR251aaB0BTLceBi; AWSALBTGCORS=G9VGYmGnv/4c+dr3wXqGzhAsPaNcV/8SDcKzoaicpnNJkj6mD4t3+96/W6Ok6iEZLmJyCHIpj10fHA2GiQ2q/ldZFvQNxbFCxr+dzuxSB4lfT1QFAkFumFQe6Jv2i8v2OJMXg1e1ZCORnGMZIV3EtuMmTZCKSR251aaB0BTLceBi; global_sid=Og_6Q3P5rRous_l-LxhO20KTwZbpRQuc1FBMlQQVtGgzMHHFxEXnzmYfp95EHmJu6nBvxHyhhfIvb-cVrIVIbqg1uY1dh48hMuwZyg==; aws-waf-token=9606bbf3-a050-40bd-b8ef-5fc7d95e2ff1:DQoAkPVTigotAAAA:zpDWoJzU5HbUGG2AXXNCMCrY/MKHgfqVC00tfrtgj3wnCmOdDfrmL+WP5jR0OedclzdHIsv7pHYfVrHFpueJeowNaXktJ7a2sXPI1HShVd8y8B5ZVCNOgW4fQIYXGHOhaJAN74xSMzcwZJnOpEkbgXJWq7SD1NTF8bJle3pNZo4bCyOjYARdRE1Ov3vHeafI70EihxHy31J6aRgw9T5YA4AHgbaZI50BHfiml09rQzZ/WMOq2OeiWj5A8RtouduBZcBmnESV9AgJGfrk0HCpSv5bWRFeFxPvw0W1uA==' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'Priority: u=4' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers' --data-raw '{prods_id}'""".format(prods_id=str(prods_id).replace("u'", '"').replace("'", '"'))
    url = 'https://groceries.morrisons.com/api/webproductpagews/v6/products'
    session.do(Request(url, use='curl', options=options, max_age=0, force_charset='utf-8'), process_prodlist, dict(context))


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
            session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))

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
                review.title = clean_text(title)
        else:
            excerpt = title

        if excerpt:
            excerpt = clean_text(excerpt)
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    next_page = revs_json.get('metadata', {}).get('nextPage')
    if next_page:
        next_url = 'https://groceries.morrisons.com/api/ecomreviews/v1/products/{ssid}/reviews?nextPage={page}'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
