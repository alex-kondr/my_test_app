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
    session.queue(Request('https://www.teknikdelar.se/', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[contains(@class, "main-nav")]/li/a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()
        session.queue(Request(url + '?order=5', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    strip_namespace(data)

    sub_cats = data.xpath('//div[@class="sub-categories"]/ul/li/a')
    if sub_cats:
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = sub_cat.xpath('@href').string()
            session.queue(Request(url + '?order=5', use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=context['cat'] + '|' + sub_name))
    else:
        process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//a[@class="product-card"]')
    for prod in prods:
        name = prod.xpath('.//p[@class="product-name"]/text()').string()
        url = prod.xpath('@href').string()

        revs = prod.xpath('.//div[@class="price-rating" and div[@style="visibility: visible;" or @style="visibility:visible;"]]')
        if revs:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url))
        else:
            return

    next_url = data.xpath('//a[span[@class="next-link"]]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    ssid = data.xpath('''//script[contains(., '{product:{id:"')]/text()''').string()
    if not ssid:
        return

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = ssid.split('{product:{id:"')[-1].split('",')[0]
    product.category = context['cat']
    product.manufacturer = data.xpath('(//tr[th[contains(., "Märke")]]/td|//li[contains(., "Märke")])/text()').string()

    mpn = data.xpath('//tr[th[contains(., "Artnr")]]/td/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//tr[th[regexp:test(., "EAN|GTIN")]]/td/text()').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[@class="review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//div[@class="date"]/text()').string()

        author = rev.xpath('.//div[@class="name"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//span[@class="star full-star"])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//div[@class="content"]/text()').string()
        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').replace('\t', '').strip(' +-*.;•–')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    revs_cnt = int(data.xpath('//span[@class="review-text"]/text()').string().replace('Omdömen', '').strip('( )'))
    if revs_cnt > 5:
        revs_url = 'https://www.teknikdelar.se/api/products/{}/reviews?offset=5&limit=5&locale=sv&sid=1'.format(product.ssid)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, revs_cnt=revs_cnt))

    elif product.reviews:
            session.emit(product)


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = simplejson.loads(data.content) or []
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('id')
        review.date = rev.get('created_at')

        author = rev.get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('score')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('review')
        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').replace('\t', '').strip(' +-*.;•–')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 5) + 5
    if offset < context['revs_cnt']:
        next_url = 'https://www.teknikdelar.se/api/products/{ssid}/reviews?offset={offset}&limit=5&locale=sv&sid=1'.format(ssid=product.ssid, offset=offset)
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, offset=offset))

    elif product.reviews:
        session.emit(product)
