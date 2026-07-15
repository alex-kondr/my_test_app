from agent import *
from models.products import *
import simplejson
import HTMLParser


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
    session.queue(Request("https://groceries.morrisons.com/categories", use='curl'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(@class, "list__item")]/a[@data-test="root-category-link"]')
    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()

        if name not in XCAT:
            session.queue(Request(url, use='curl'), process_category, dict(cat=name))


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

    options = """--compressed -X PUT -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:152.0) Gecko/20100101 Firefox/152.0' -H 'Accept: application/json; charset=utf-8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Referer: https://groceries.morrisons.com/categories/fruit-veg/176738?sortBy=favorite' -H 'X-CSRF-TOKEN: e34f8243-42f0-4ef5-ac3e-48089690a644' -H 'client-route-id: bede6f1d-09c5-4b1d-86d9-a92d94083675' -H 'ecom-request-source: web' -H 'ecom-request-source-version: 2.0.0-2026-07-14-06h19m43s-9876d06b' -H 'page-view-id: 88456d47-06e6-462d-aa6a-8c1494aadf64' -H 'content-type: application/json; charset=utf-8' -H 'Origin: https://groceries.morrisons.com' -H 'Alt-Used: groceries.morrisons.com' -H 'Connection: keep-alive' -H 'Cookie: VISITORID=kfKLgza8qyKm2xYv3Hvq0oDN2ztu-g8_BRtnImxBkzBVHa-R6qCB-BuXxfzK5GksRWSgmRuhXf3YufWFyjDUJqGMKZ_w0pC3_JqDsg==; contentExperienceUserId=8690b9ff-8d83-42bf-bde0-375947bd46f2; language=en-GB; AWSALB=mYgqBEUwA8j3igiBSMsPVdUHa6d9x6cH9kXRDZIPu8k+18TTGjHw2yQXmF0sf+WMi3fvmJ7OU310/MQ8M0HTUkwq+T5wMH8QHpGvrl/VKKuy/j5jRiCtqzhsujfl; AWSALBCORS=mYgqBEUwA8j3igiBSMsPVdUHa6d9x6cH9kXRDZIPu8k+18TTGjHw2yQXmF0sf+WMi3fvmJ7OU310/MQ8M0HTUkwq+T5wMH8QHpGvrl/VKKuy/j5jRiCtqzhsujfl; OptanonConsent=isGpcEnabled=0&datestamp=Wed+Jul+15+2026+16%3A10%3A25+GMT%2B0300+(%D0%B7%D0%B0+%D1%81%D1%85%D1%96%D0%B4%D0%BD%D0%BE%D1%94%D0%B2%D1%80%D0%BE%D0%BF%D0%B5%D0%B9%D1%81%D1%8C%D0%BA%D0%B8%D0%BC+%D0%BB%D1%96%D1%82%D0%BD%D1%96%D0%BC+%D1%87%D0%B0%D1%81%D0%BE%D0%BC)&version=202501.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=fd1f1182-bd19-465d-8b20-0e91dc6ec5c7&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0003%3A1%2CC0004%3A1%2CC0002%3A1&intType=1&geolocation=UA%3B51&AwaitingReconsent=false; OptanonAlertBoxClosed=2026-07-14T14:04:59.588Z; AWSALBTG=Ln6GALRFfbyel72OGCEL1n6m7YwxiUeFOSIJjkXX9xdr/t9ad5mdJoDDJzz1SDYLD4BHYgNR1brH7QXU91q7wqZjYmdfbqxEBv9D3g/MG9ohiEtZLOUwNl0t472VCV5gvMiUqzTedQyu4ZBMo7FDk303HP49buYzbg3ZR3VT/SuX; AWSALBTGCORS=Ln6GALRFfbyel72OGCEL1n6m7YwxiUeFOSIJjkXX9xdr/t9ad5mdJoDDJzz1SDYLD4BHYgNR1brH7QXU91q7wqZjYmdfbqxEBv9D3g/MG9ohiEtZLOUwNl0t472VCV5gvMiUqzTedQyu4ZBMo7FDk303HP49buYzbg3ZR3VT/SuX; global_sid=AmLidjNnFIhaLkFQHEkWsdAH-nKQHErAZonJyxAfaB0vkmtQW30GQPYo5dxhjmRlrC_pj1KM1zd3RT3EHprw-qEy5E_ytnFNoMkB2Q==; aws-waf-token=b9477174-b84f-482f-ba04-2e3466b0622a:DQoAiJBbihkbAAAA:zFS3UrSQV303uG6TX1S7HSJ/3I9FdtfrDWhWGSFBenYixg2MT+U4triisYuxEa/PRjDNgJmMgwuRn4Gaelp/c+ZZMgDa48cWHE/ItLP60vh7nOklvKutzlVPP07jXaQS27DIsG9Yvx9os8+ozGeeqN4Asq6jp01SUdbqDCPUWALxIhprhIxMrHMXV0LBplHxLrqGDMYjLPaVXZ2VGHQWiJDARTyuVQ0PSz+MESA+UTHxyKZm1waPqjzYeiBu05h/T6cN6J328hYmAOAqKs/YSbirtHdmiN/FR2g2Vg==' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'Priority: u=4' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers' --data-raw '{prods_id}'""".format(prods_id=str(prods_id).replace("u'", '"').replace("'", '"'))
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
            session.do(Request(revs_url, use='curl'), process_reviews, dict(product=product))

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
                review.title = h.unescape(remove_emoji(title)).replace('\\x27', "'").replace('\\x26', '').replace('â\\x80¦', '').replace(u'â\x80¦', u'').replace('\xe2\x80\x9c', '"').replace('\xe2\x80\x9d', '"').replace(u'\xe2\x80\x9c', '"').replace(u'\xe2\x80\x9d', '"').replace('\\x', "'").replace(u'â\x80\x98', u"'").replace(u'\xe2\x80\x98', u"'").replace(u'Ã\x80', u'À').replace(u'\xc3\x80', u'À').replace(u'â\x98\x86', u'').replace(u'\xe2\x98\x86', u'').replace(u'â\x80\x94', u'—').replace(u'Ã\x9c', u'Ü').replace(u'â\x80\x93', u'-').replace(u'Â£', u' ').replace(u' Â', u'').replace(u'Â\xa0', u' ').replace(u'Â©', u'©').strip(u'Â ')
        else:
            excerpt = title

        if excerpt:
            excerpt = h.unescape(remove_emoji(excerpt)).replace('\n', '').replace('\\x27', "'").replace('\\x26', '').replace('â\\x80¦', '').replace(u'â\x80¦', u'').replace('\xe2\x80\x9c', '"').replace('\xe2\x80\x9d', '"').replace(u'\xe2\x80\x9c', '"').replace(u'\xe2\x80\x9d', '"').replace('\\x', "'").replace(u'â\x80\x98', u"'").replace(u'\xe2\x80\x98', u"'").replace(u'Ã\x80', u'À').replace(u'\xc3\x80', u'À').replace(u'\xe2\x98\x86', u'').replace(u'â\x80\x94', u'—').replace(u'Ã\x9c', u'Ü').replace(u'â\x80\x93', u'-').replace(u'Â£', u' ').replace(u' Â', u' ').replace(u'Â\xa0', u' ').replace(u'Â©', u'©').strip(u'Â ')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    next_page = revs_json.get('metadata', {}).get('nextPage')
    if next_page:
        next_url = 'https://groceries.morrisons.com/api/ecomreviews/v1/products/{ssid}/reviews?nextPage={page}'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url, use='curl'), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
