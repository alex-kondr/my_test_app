from agent import *
from models.products import *
import simplejson


XCAT = ['Spor&Outdoor']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    options = "-H 'Cookie: platform=web; __cflb=0H28vSBxxmVRpbspxYA1XYcVBYMRWUgCe5z4QQY4Z3A; __cfruid=9a2b43df65360d19f57a1dadb0afae4a15f5505b-1663146084; _cfuvid=27bUCGqiLtrjrb1Ip0m6FTYstxzmpOYARvjgHOwqr.U-1663146084709-0-604800000; anonUserId=cf7131a0-340b-11ed-b9f6-8d53175bbfd8; functionalConsent=false; performanceConsent=false; targetingConsent=false; OptanonConsent=isGpcEnabled=0&datestamp=Wed+Sep+14+2022+12%3A01%3A52+GMT%2B0300+(Eastern+European+Summer+Time)&version=6.30.0&isIABGlobal=false&hosts=&genVendors=&consentId=f2a83bcf-9898-48ff-b42b-2faab9d0cfde&interactionCount=1&landingPath=https%3A%2F%2Fwww.trendyol.com%2Fen%2Fselect-country&groups=C0002%3A0%2CC0004%3A0%2CC0003%3A0%2CC0001%3A1; storefrontId=1; countryCode=TR; language=tr'"
    session.queue(Request("https://www.trendyol.com/", use="curl", options=options, max_age=0, force_charset="utf-8"), process_frontpage, dict(options=options))


def process_frontpage(data, context, session):
    cats_json = data.xpath("""//script[contains(., '"items":')][contains(., "Children")]/text()""").string()
    if not cats_json:
        return

    cats_json = simplejson.loads(cats_json.split('__=')[-1].strip('; '))
    cats1 = cats_json.get('items', [])
    for cat1 in cats1:
        name1 = cat1.get('Name')

        if name1 not in XCAT:
            sub_cats = cat1.get('Children', [])
            for sub_cat in sub_cats:
                cats2 = sub_cat.get('Children', [])
                for cat2 in cats2:
                    name2 = cat2.get('Name')
                    cats3 = cat2.get('Children', [])
                    for cat3 in cats3:
                        name3 = cat3.get('Name')
                        url = 'https://www.trendyol.com/' + cat3.get('Url')
                        session.queue(Request(url, use="curl", force_charset="utf-8", max_age=0), process_prodlist, dict(context, cat=name1+'|'+name2+'|'+name3))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="p-card-wrppr with-campaign-view"]')
    for prod in prods:
        name = prod.xpath('.//span[contains(@class, "cntnr-name")]/@title').string()
        brand = prod.xpath('.//span[contains(@class, "cntnr-ttl")]/@title').string()
        url = prod.xpath('.//a/@href').string()
        ssid = prod.xpath('@data-id').string()

        revs_cnt = prod.xpath('.//span[@class="ratingCount"]/text()').string()
        if revs_cnt:
            revs_cnt = int(revs_cnt.strip(' ()'))
            if revs_cnt > 0:
                session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, brand=brand, url=url, ssid=ssid))

    prods_cnt = data.xpath('//div[contains(., "sonuç listeleniyor")]/text()').string(multiple=True)
    if prods_cnt:
        if '+' in prods_cnt:
            prods_cnt = prods_cnt.replace('+', '').replace('.', '')

        prods_cnt = int(prods_cnt.split(' sonuç')[0].split('için ')[-1])
        offset = context.get('offset', 0) + 24
        if prods_cnt > offset:
            next_page = context.get('page', 1) + 1
            next_url = 'https://www.trendyol.com/cocuk-elbise-x-g3-c56?pi=' + str(next_page)
            session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(context, offset=offset, page=next_page))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.manufacturer = context['brand']
    product.category = context['cat']
    product.url = context['url']
    product.ssid = context['ssid']

    info = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
    if info:
        info = simplejson.loads(info)
        mpn = info.get('hasVariant', [{}])[0].get('gtin13')
        if mpn:
            product.properties.append(ProductProperty(type='id.manufacturer', value=str(mpn)))

    revs_url = 'https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/review/{}?merchantId=172584&storefrontId=1&culture=tr-TR&pageSize=50&page='.format(product.ssid)
    session.do(Request(revs_url + '0', use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, revs_url=revs_url))

    if product.reviews:
        session.emit(product)


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    revs = revs_json.get('result', {}).get('productReviews', {})
    if not revs:
        return

    revs = revs.get('content', [])
    for rev in revs:
        review = Review()
        review.url = product.url
        review.type = 'user'
        review.ssid = str(rev['id'])
        review.date = rev.get('commentDateISOtype')

        title = rev.get('commentTitle')
        if title:
            review.title = title.encode().decode()

        author = rev.get('userFullName')
        if author:
            author = author.encode().decode()
            review.authors.append(Person(name=author, ssid=author))

        is_verified = rev.get('trusted')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('reviewLikeCount')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        is_recommended = rev.get('userLiked')
        if is_recommended:
            review.properties.append(ReviewProperty(value=True, type='is_recommended'))

        grade_overall = rev.get('rate')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('comment')
        if excerpt:
            excerpt = excerpt.encode().decode()

            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    revs_cnt = revs_json.get('result', {}).get('productReviews', {}).get('totalElements')
    offset = context.get('offset', 0) + 50
    if revs_cnt and int(revs_cnt) > offset:
        next_page = context.get('page', 0) + 1
        next_url = context['revs_url'] + str(next_page)
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, offset=offset, page=next_page))
