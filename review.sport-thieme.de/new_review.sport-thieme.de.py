from agent import *
from models.products import *
import re
import simplejson
import urllib


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: cross-site' -H 'Connection: keep-alive' -H 'Alt-Used: www.sport-thieme.de' -H 'Cookie: __Secure-authjs.callback-url=https://www.sport-thieme.de; qwik-session=eyJhbGciOiJIUzI1NiJ9.eyJzZXNzaW9uSWQiOiI1MDAwNTQ0Yi0zNzg2LTQ2ZmUtODI3Mi1jZGRkZmUyNjk0MGQiLCJleHAiOjE3NDc5MjIyODUsImlhdCI6MTc0NDAzNDI4NX0.WVIy72PJ8gHzrN-a-65xQCPe0tJgaP0cDfgF9SiqL18; marketingOrigin=W0-OA; __qw_i=0; lastseen=["2747402","2570802","1997255","2824202","1080908","2611701","1869369"]; _dd_s=logs=1&id=e3e4e414-e11d-48af-aec5-81dfc4643413&created=1744032451989&expire=1744035545577; aws-waf-token=632fa5e9-74e2-42b9-a655-f4d64c658dd9:DQoAv/NiCdc3AAAA:dhTYkykvv5BYbNShPJn8DUBDiGKrYnNHNIWm7wI8VoTO+vwLgW+pQpIyJGrEdpt0xQ2774U8AB8+0j2lGjv02fQiycAh3IHODkQL90CQqr2SG0MecOHyysjtYWBwqHYzqpONoCHZW45RI9+8IjJ5NGZlcHCbNf/1WzBKXcLFM9aJ4C/VNBWeT9Gz9/LwsxKJ/6s85LzAxVIA47RpcocrzvUlWRC3dCA21g3QX4wo2Wtto9DsAG+N0kez7dfCkNHK5ZMb9VWeOw==' -H 'Priority: u=0, i'"""


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
            excerpt = remove_emoji(excerpt.replace('&#34;', '"').replace('\r\n', '')).strip()
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
