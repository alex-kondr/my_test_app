from agent import *
from models.products import *
import simplejson
import re
import time
import random


XCAT = ['New', 'Collections', 'Corporate Enquiries', 'Inspiration', 'Shop All', 'Sale']


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
    session.queue(Request('https://brabantia.com.au/', force_charset='utf-8'), process_frontpage, {})


def process_frontpage(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    cats = data.xpath('//nav[@role="navigation"]/div/div')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('div/div/div[contains(@class, "content")]/div')

            for cat1 in cats1:
                cat1_name = cat1.xpath('a[contains(@class, "[700]")]/text()').string()

                if cat1_name not in XCAT:
                    subcats = cat1.xpath('a[contains(@class, "[16px]")]')
                    if subcats:
                        for subcat in subcats:
                            subcats_name = subcat.xpath('text()').string()
                            url = subcat.xpath('@href').string()
                            session.queue(Request(url, force_charset='utf-8'), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcats_name))
                    else:
                        url = cat1.xpath('a/@href').string()
                        session.queue(Request(url, force_charset='utf-8'), process_prodlist, dict(cat=name+'|'+cat1_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    prods = data.xpath('//div[@data-product-id]')
    for prod in prods:
        prod_name = prod.xpath('.//h3/a/text()').string()
        url = prod.xpath('.//h3/a/@href').string().split('?')[0]
        ssid = prod.xpath('.//@data-product-id').string()
        session.queue(Request(url, force_charset='utf-8'), process_product, dict(context, name=prod_name, url=url, ssid=ssid))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = data.xpath('//tr[contains(td/text(), "SKU")]/td[not(contains(., "SKU"))]/text()').string()
    product.category = context['cat']
    product.manufacturer = 'Brabantia'

    ean = data.xpath('//tr[contains(td/text(), "EAN")]/td[not(contains(., "EAN"))]/text()').string()
    if ean:
        ean = ean.strip(" '")
        if ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_url = 'https://api-cdn.yotpo.com/v3/storefront/store/cKoXl68lGe6bxTnuIHwKxMhTqrXL8Wy7CPseJnLa/product/{}/reviews?page=1&perPage=5&sort=date,images,badge,rating'.format(product.ssid)
    session.queue(Request(revs_url, force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('reviews', [])
    for rev in revs:
        if rev.get('language') != 'en' or rev.get('syndicationData') or rev.get('groupingData'):
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('user', {}).get('displayName')
        author_ssid = rev.get('user', {}).get('userId')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=str(author_ssid)))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('score')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.get('votesUp')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('votesDown')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        is_verified_buyer = rev.get('verifiedBuyer')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('title')
        excerpt = rev.get('content')
        if excerpt and len(remove_emoji(excerpt).replace('\n', '').strip()) > 2:
            if title:
                review.title = remove_emoji(title).replace('\n', '').strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = context.get('revs_cnt', revs_json.get('pagination', {}).get('total', 0))
    offset = context.get('offset', 0) + 5
    if offset < revs_cnt:
        next_page = context.get('page', 1) + 1
        revs_url = 'https://api-cdn.yotpo.com/v3/storefront/store/cKoXl68lGe6bxTnuIHwKxMhTqrXL8Wy7CPseJnLa/product/{ssid}/reviews?page={page}&perPage=5&sort=date,images,badge,rating'.format(ssid=product.ssid, page=next_page)
        session.do(Request(revs_url, max_age=0, force_charset='utf-8'), process_reviews, dict(product=product, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
