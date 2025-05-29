from agent import *
from models.products import *
import simplejson
import re


XCAT = ['All Backpacks', 'Shop by Activity']
OPTIONS = "-H 'Content-Type: application/json' -H 'Junip-Store-Key: hbmj1oacPxBY3cLHUe3JVB5N'"


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
    session.queue(Request("https://caribee.com/", use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[@class="#main-nav-item @dropdown"]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('div/ul/li/a')
            for cat1 in cats1:
                name1 = cat1.xpath('text()').string()
                url = cat1.xpath('@href').string()

                if name1 not in XCAT:
                    session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name+"|"+name1))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "product-card") and a]')
    for prod in prods:
        name = prod.xpath('.//div[contains(@class, "product-heading")]/text()').string()
        url = prod.xpath('a/@href').string()

        revs_count = prod.xpath('.//div[contains(@class, "reviews-counter")]/text()').string()
        if revs_count and int(revs_count) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//span[contains(@class, "junip-product-review")]/@data-product-id').string()
    product.category = context['cat']

    prod_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.sku = prod_json.get('sku')
        product.manufacturer = prod_json.get('brand', {}).get('name')

        ean = prod_json.get('gtin')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_url = 'https://apid.juniphq.com/v2/products/remote/{ssid}/reviews?sort_field=created_at&sort_order=desc&page_size=5&v=hbmj1oacPxBY3cLHUe3JVB5N'.format(ssid=product.ssid)
    session.do(Request(revs_url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('data', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.ssid = str(rev['id'])
        review.url = product.url

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('customer')
        if author:
            first_name = author.get('first_name')
            last_name = author.get('last_name')
            author_ssid = str(author.get('id'))
            if first_name and last_name:
                author_name = first_name + " " + last_name
                review.authors.append(Person(name=author_name, ssid=author_ssid))
            elif first_name:
                review.authors.append(Person(name=first_name, ssid=author_ssid))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_recommended = rev.get('would_recommend')
        if is_recommended:
            review.add_property(value=True, type='is_recommended')

        is_verified = rev.get('verified_buyer')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('up_vote_count')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('down_vote_count')
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.get('title')
        excerpt = rev.get('body')
        if excerpt and len(remove_emoji(excerpt).replace('\n', ' ').replace('\]', '').strip()) > 2:
            if title:
                review.title = remove_emoji(title.replace('\]', '')).strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', ' ').replace('\]', '').strip()
            if excerpt:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    after = revs_json.get('meta', {}).get('after')
    if after:
        next_url = 'https://apid.juniphq.com/v2/products/remote/{ssid}/reviews?page_size=5&sort_field=created_at&sort_order=desc&page_after={after}&v=hbmj1oacPxBY3cLHUe3JVB5N'.format(ssid=product.ssid, after=after)
        session.do(Request(next_url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
