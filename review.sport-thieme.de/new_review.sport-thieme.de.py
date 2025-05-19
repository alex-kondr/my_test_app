from agent import *
from models.products import *
import re
import simplejson
import urllib
import HTMLParser


h = HTMLParser.HTMLParser()
OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: cross-site' -H 'Connection: keep-alive' -H 'Cookie: qwik-session=eyJhbGciOiJIUzI1NiJ9.eyJzZXNzaW9uSWQiOiI0MWM5MDUyNi1hMGUzLTQwMWEtOWE5Mi05ZGZkMDg5MDI2NmQiLCJleHAiOjE3NTE1NjkxMzgsImlhdCI6MTc0NzY4MTEzOH0.6_Ctz5gfGiRk7xCUzxSkg4OkOA0khzbSa65uzt47O5I; marketingOrigin=W0-OA; __Secure-authjs.callback-url=https://www.sport-thieme.de; __qw_i=0; _dd_s=logs=1&id=78aca75c-0ea9-4211-94ea-90fd0e42e084&created=1747681173642&expire=1747683299202; lastseen=["2378204","2715706"]; aws-waf-token=7127b979-a254-4a54-bddb-d8c377cfd152:HAoArS2Hh2orAQAA:xiDlCxD37hO0Tt/dYkcELrGEn+fq5nRZLyxhNHOn5avXzBRpyr7pWdHfFl3HbN1H9los39bwufWwCcA60HLgbui5EFeRBkKuvUaF9PeHvVYB2ONaASdtJEx4IZlllU8HY9iT48av0z+WYV1UNk02VOCcfCa0gStzMGic1AFA2N+e6Mx4pGDJ7XY399QBBwM9qLalvefdYTSYQhVBHt2648Q=' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers'"""


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
    session.queue(Request('https://www.sport-thieme.de/', use='curl', options=OPTIONS, force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//a[@class="category-link"]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', options=OPTIONS, force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@data-testid="list-product"]')
    for prod in prods:
        name = prod.xpath('.//h3[contains(@class, "title")]/text()').string()
        url = prod.xpath('.//a[@class="absoluteLink"]/@href').string()

        revs = prod.xpath('.//span[@stars]')
        if revs:
            session.queue(Request(url, use='curl', options=OPTIONS, force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[svg[@aria-label="Chevron Right Icon"]]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', options=OPTIONS, force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('=')[-1]
    product.sku = product.ssid
    product.category = context['cat'] + '|' + urllib.unquote(product.url.split('/')[-2].encode('utf-8'))

    manufacturer = data.xpath('//a[@class="brandLink"]/@href').string()
    if not manufacturer:
        manufacturer = data.xpath('//div[contains(@class, "formattedVariantNumber")]//text()').string(multiple=True)

    if manufacturer:
        product.manufacturer = manufacturer.split('/')[-1]

    mpn = data.xpath('(//p[contains(., "Artikelnummer")])[1]/span//text()').string(multiple=True)
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    context['product'] = product

    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs_json = data.xpath('''//script[contains(., '"@type":"Review"')]/text()''').string()
    if not revs_json:
        return

    revs = simplejson.loads(revs_json).get('review', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.get('datePublished')

        author = rev.get('author', {}).get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('reviewRating', {}).get('ratingValue')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('reviewBody')
        if excerpt:
            excerpt = excerpt = h.unescape(remove_emoji(excerpt).replace('\r\n', '')).strip()
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
