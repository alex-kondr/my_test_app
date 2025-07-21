from agent import *
from models.products import *
import simplejson
import re


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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.rakuten.co.jp/category/?l-id=top_normal_gmenu_d_list', use='curl'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="gtc-genreUnit"]')
    for cat in cats:
        name = cat.xpath('a/div[contains(@class, "title")]/text()').string()

        sub_cats = cat.xpath('ul/li/a')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = sub_cat.xpath('@href').string()
            session.queue(Request(url, use='curl'), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[@data-id]')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('.//h2[contains(@class, "title")]/a/text()').string()
        product.url = prod.xpath('div/a[img]/@href').string()
        product.ssid = prod.xpath('@data-id').string()
        product.sku = product.ssid
        product.category = context['cat']

        rating = prod.xpath('.//span[@class="score"]')
        if rating:
            shop_id = prod.xpath('@data-shop-id').string()
            options = """-X POST -H 'Accept-Encoding: deflate' -H 'Content-Type: application/json; charset=UTF-8' -H 'authkey: isrlPcMjUuXCVBUTVh91ZcHEfoI45CmPR' --data-raw '{"common":{"params":{"device":"pc"},"include":["itemReviewList"]},"features":{"itemReviewList":{"params":{"shopId":{""" + shop_id + """},"itemId":{""" + product.ssid + """},"page":"1","hits":30}}}}'"""
            
            print('options=', options)
            
            revs_url = 'https://web-gateway.rakuten.co.jp/review/itemshopreviewlist/get/v1'
            session.do(Request(revs_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(product=product, shop_id=shop_id))

    next_url = data.xpath('//a[contains(@class, "nextPage")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_prodlist, dict(context))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs_json = simplejson.loads(data.content).get('body', {}).get('itemReviewList', {}).get('data', {})

    revs = revs_json.get('reviews', [])
    
    print('revs=', revs)
    
    
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('key')
        review.date = rev.get('postDate')

        author = rev.get('nickname')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.get('helpfulCount')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        title = rev.get('title')
        excerpt = rev.get('body')
        if excerpt and len(remove_emoji(excerpt).strip()) > 2:
            if title:
                review.title = remove_emoji(title).strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    next_page = revs_json.get('hasNextPage', False)
    if next_page:
        next_page = context.get('page', 1) + 1
        options = """-X POST -H 'Accept-Encoding: deflate' -H 'Content-Type: application/json; charset=UTF-8' -H 'authkey: isrlPcMjUuXCVBUTVh91ZcHEfoI45CmPR' --data-raw '{"common":{"params":{"device":"pc"},"include":["itemReviewList"]},"features":{"itemReviewList":{"params":{"shopId":{""" + context['shop_id'] + """},"itemId":{""" + product.ssid + """},"page":""" + str(next_page) + ""","hits":30}}}}'"""
        revs_url = 'https://web-gateway.rakuten.co.jp/review/itemshopreviewlist/get/v1'
        session.do(Request(revs_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(context, product=product, page=next_page))

    elif product.reviews:
        session.emit(product)