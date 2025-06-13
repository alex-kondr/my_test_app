from agent import *
from models.products import *
import re
import simplejson


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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.bangerhead.se/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@class="child-ul"]')
    for cat in cats:
        name = cat.xpath('li[@class]//span[@class="title"]/text()').string()

        if name:
            sub_cats = cat.xpath('li[not(@class)]/a')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                cat_id = sub_cat.xpath('@cid').string()
                options = "--compressed -X POST --data-raw 'filter_params=%7B%7D&funk=get_filter&limits=24&category_id={}&brand_id=&campaign_id=&property_value_id=&offset=0&Sort=SortSpecialDESC-111'".format(cat_id)
                session.do(Request('https://www.bangerhead.se/shop', use='curl', force_charset='utf-8', options=options, max_age=0), process_prodlist, dict(cat=name + '|' + sub_name, cat_id=cat_id))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="img_card"]/a')
    for prod in prods:
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, url=url))

    if prods:
        offset = context.get('offset', 0) + 24
        options = "--compressed -X POST --data-raw 'filter_params=%7B%7D&funk=get_filter&limits=24&category_id={cat_id}&brand_id=&campaign_id=&property_value_id=&offset={offset}&Sort=SortSpecialDESC-111'".format(cat_id=context['cat_id'], offset=offset)
        session.do(Request('https://www.bangerhead.se/shop', use='curl', force_charset='utf-8', options=options, max_age=0), process_prodlist, dict(context, offset=offset))


def process_product(data, context, session):
    product = Product()
    product.name = data.xpath('//h1[@class="product-name"]/b/text()').string()
    product.url = context['url']
    product.ssid = data.xpath('//h1[@class="product-name"]/span[@id="ArtnrFalt"]/text()').string()
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//h1[@class="product-name"]/span[@id="varumarke"]//text()').string(multiple=True)

    prod_info = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if prod_info and '"mpn": "' in prod_info:
        mpn = prod_info.split('"mpn": "', 1)[-1].split('", "')[0].strip()
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

    options = "-H 'X-GMF-Merchant-Id: 8182'"
    revs_url = 'https://api.gamifiera.com/v3/comments/search?product_id%3Agroup={}&type=product_review&link=product_review&skip=0&take=5'.format(product.ssid)
    session.do(Request(revs_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('comments', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = ((rev.get('author', {}).get('firstName') or '') + ' ' + (rev.get('author', {}).get('lastName') or '')).strip()
        author_ssid = rev.get('author', {}).get('id')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=str(author_ssid)))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('content', {}).get('ratings', {}).get('product_score', {}).get('value')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        pros = rev.get('content', {}).get('pros', [])
        for pro in pros:
            pros_ = pro.split('•')
            for pro in pros_:
                pro = remove_emoji(pro).replace('\t', '').strip(' +-*.;•–')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

        cons = rev.get('content', {}).get('cons', [])
        for con in cons:
            cons_ = con.split('•')
            for con in cons_:
                con = remove_emoji(con).replace('\t', '').strip(' +-*.;•–')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

        is_verified_buyer = rev.get('isVerified')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('votes', {}).get('upvotes')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('votes', {}).get('downvotes')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.get('content', {}).get('title')
        excerpt = rev.get('content', {}).get('text')
        if excerpt and len(remove_emoji(excerpt).replace('\t', '').replace('\n', ' ').replace('  ', ' ').strip(' +-*.')) > 2:
            if title:
                review.title = remove_emoji(title).replace('\t', '').replace('\n', ' ').replace('  ', ' ').strip(' +-*.')
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\t', '').replace('\n', ' ').replace('  ', ' ').strip(' +-*.')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = revs_json.get('totalCount')
    offset = context.get('offset', 0) + 5
    if offset < revs_cnt:
        options = "-H 'X-GMF-Merchant-Id: 8182'"
        revs_url = 'https://api.gamifiera.com/v3/comments/search?product_id%3Agroup={ssid}&type=product_review&link=product_review&skip={offset}&take=5'.format(ssid=product.ssid, offset=offset)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(product=product, offset=offset))

    elif product.reviews:
        session.emit(product)
