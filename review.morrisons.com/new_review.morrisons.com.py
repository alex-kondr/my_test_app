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
    return h.unescape(remove_emoji(text)).replace('\n', '').replace('\\x27', "'").replace('\\x26', '').replace('â\\x80¦', '').replace(u'â\x80¦', u'').replace('\xe2\x80\x9c', '"').replace('\xe2\x80\x9d', '"').replace(u'\xe2\x80\x9c', '"').replace(u'\xe2\x80\x9d', '"').replace('\\x', "'").replace(u'â\x80\x98', u"'").replace(u'\xe2\x80\x98', u"'").replace(u'Ã\x80', u'À').replace(u'\xc3\x80', u'À').replace(u'\xe2\x98\x86', u'').replace(u'â\x80\x94', u'—').replace(u'Ã\x9c', u'Ü').replace(u'â\x80\x93', u'-').replace(u'Â£', u' ').replace(u' Â', u' ').replace(u'Â\xa0', u' ').replace(u'Â©', u'©').replace(u'Ã¼', u'ü').replace(u'Ã©', u'é').replace(u'Ã¤', u'ä').replace(u'Ã¡', u'á').replace(u'Ã±', u'ñ').replace(u'\x80\x91', u'-').strip(u'Â ')


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
    session.queue(Request("https://groceries.morrisons.com/categories", use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(@class, "list__item")]/a[@data-test="root-category-link"]')
    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_category, dict(cat=name))


def process_category(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    data_json = data.xpath('//script[@data-test="initial-state-script"]/text()').string()
    if not data_json:
        return

    prods_id = []

    data_json = simplejson.loads(data_json.replace('window.__INITIAL_STATE__=', ''))
    productGroups = data_json.get('data', {}).get('products', {}).get('catalogue', {}).get('data', {}).get('productGroups', [])
    for prod in productGroups:
        prods_id += prod.get('products')

    options = """--compressed -X PUT -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:154.0) Gecko/20100101 Firefox/154.0' -H 'Accept: application/json; charset=utf-8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'X-CSRF-TOKEN: f04a865c-2fdb-43cb-9ffd-2e15bca2b949' -H 'client-route-id: ab364d22-b7e2-4725-b06e-46e91f81eb03' -H 'ecom-request-source: web' -H 'ecom-request-source-version: 2.0.0-2026-08-26-07h29m53s-cf43ac0c' -H 'page-view-id: fe857557-8de0-4242-9e7f-457274d1b55a' -H 'content-type: application/json; charset=utf-8' -H 'Cookie: VISITORID=Q6pwJGzGqG017OofSHGF3Rtg9JCMwcoO2gsr2Sh82z9Dpf7LpYxFqh18E1Mep_ebVoh8kREblz20JeUwFtuQVDzHWK2Yl9lohE2CgA==; contentExperienceUserId=58a2d1a1-b232-48e3-9d8a-9c7cb4295689; language=en-GB; global_sid=yjxtVOTZZytRnu0FPRCzppHgjRvnKZKiGxWC2xfsNCaSKnE9bY1q9SqzpCbfBnaGaGbIhjCjzezoPpiWgDkfv1aq5gA-IENUVgl8yA==; AWSALB=ZoRCcCB6RdXReRE6ikelvqKjEfD8Lf8+tiG0GL3Yx3fLZY82ofJyQI+ZjrZpRJtqvweT8ihcnfvpkRGf14A2nxMflTqSUzKe4xXIqnRmSpYgePP3F8PXZwt47DEl; AWSALBCORS=ZoRCcCB6RdXReRE6ikelvqKjEfD8Lf8+tiG0GL3Yx3fLZY82ofJyQI+ZjrZpRJtqvweT8ihcnfvpkRGf14A2nxMflTqSUzKe4xXIqnRmSpYgePP3F8PXZwt47DEl; OptanonConsent=isGpcEnabled=0&datestamp=Fri+Aug+28+2026+07%3A44%3A05+GMT%2B0300+(%D0%B7%D0%B0+%D1%81%D1%85%D1%96%D0%B4%D0%BD%D0%BE%D1%94%D0%B2%D1%80%D0%BE%D0%BF%D0%B5%D0%B9%D1%81%D1%8C%D0%BA%D0%B8%D0%BC+%D0%BB%D1%96%D1%82%D0%BD%D1%96%D0%BC+%D1%87%D0%B0%D1%81%D0%BE%D0%BC)&version=202501.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=36d3ef59-6428-47f8-9048-5f654c1fb79b&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0003%3A1%2CC0004%3A1%2CC0002%3A1&intType=1&geolocation=UA%3B51&AwaitingReconsent=false; aws-waf-token=9f562f7a-bffa-45a3-97ba-2b86169824d9:IAoAhhIghCEIAAAA:aMYnGuAIW+ClxUfwPOTw7orzfv4qZQdqyLc4wMOK+xoTt1fa0Q0w06IUCN7mZROyT8UTELQZE1Op0gLUph8KxxWEC/9dCD6KiqGVcUTlJL5O2GiiLT7XK6eJpHLQFBvFXQ+Vlujxi4JhCGNc+sNIyHbaWUQ6diuW30l1s83GC6gVEVFZQiMOum24mwCXAinALUbmlG3ERFVhWtdGjBQGQBh03tMUZKcngRJeRFPN/c6dTlsD472/XOoWZyUnPjATSnpdzTUt0i5grxLZEQ7OH8Q4l2rV5N4SZ5CDWg==; OptanonAlertBoxClosed=2026-08-28T04:43:10.961Z' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'Priority: u=4' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers' --data-raw '{prods_id}'""".format(prods_id=str(prods_id).replace("u'", '"').replace("'", '"'))
    url = 'https://groceries.morrisons.com/api/webproductpagews/v6/products'
    session.do(Request(url, use='curl', options=options, max_age=0, force_charset='utf-8'), process_prodlist, dict(context))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
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


def process_reviews(data: Response, context: dict[str, str], session: Session):
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
            author = remove_emoji(author).strip()
            if len(author) > 1:
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
        if excerpt and len(clean_text(excerpt)) > 2:
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
