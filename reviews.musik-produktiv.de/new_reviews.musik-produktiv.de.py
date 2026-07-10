from agent import *
from models.products import *
import simplejson
import re


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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.musik-produktiv.de/', use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[contains(@class, "category")]/a[contains(@class, "link")]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_catlist, dict(cat=context.get('cat', '') +'|'+name))

    if not cats:
        process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//a[contains(@class, "product-name")]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@data-focus-id="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//button/@data-product-id').string()
    product.sku = data.xpath('//span[contains(@class, "ordernumber")]/text()').string()
    product.category = context['cat'].replace(' und mehr', '').strip('| ')
    product.manufacturer = data.xpath('//div/a[contains(@class, "product-manufacturer")]/@title').string()

    prod_json = data.xpath('''//script[contains(., '"@type":"Product"') and not(@data-ga-product-id)]/text()''').string()
    if not prod_json:
        return

    prod_json = simplejson.loads(prod_json)

    mpn = prod_json[0].get('mpn')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = prod_json[0].get('gtin13')
    if ean and str(ean).isdigit() and len(str(ean)) > 10:
        product.add_property(type='id.ean', value=str(ean))

    revs = data.xpath('//div[@id="review-list"]/div/div[contains(@class, "review-item")]')
    revs_cnt = prod_json.get('aggregateRating', {}).get('ratingCount', 0)
    
    if len(revs) != int(revs_cnt):
        raise ValueError("!!!!!!!!!!!")

    revs = prod_json[0].get('review', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('datePublished')
        if date:
            review.date = date.split('T')[-1]

        author = rev.get('author', {}).get('name')
        if author:
            author = remove_emoji(author).strip()
            if author:
                review.authors.append(Person(name=author, ssid=author))
            else:
                author = None

        grade_overall = rev.get('reviewRating', {}).get('ratingValue')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        title = rev.get('name')
        excerpt = rev.get('description')
        if excerpt and len(remove_emoji(excerpt).replace('<br/>', ' ').strip()) > 2:
            if title:
                review.title = remove_emoji(title).strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('<br/>', ' ').strip()
            if len(excerpt) > 1:
                review.add_property(type="excerpt", value=excerpt)

                review.ssid = review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)
