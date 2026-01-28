from agent import *
from models.products import *
import simplejson
import re


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: client_key=eb0d; aws-waf-token=33fe9b72-74e9-46c6-a49e-858ffff22840:CAoApbtVgdYIAAAA:TFy9DqjVclYTB4fXHJUtSSQ0/iYXoFn6oO3dw0iq1T2xU54nEXM4l+L5nougxjtgaRFiefvG4Bj/wz8nmK31EZk9Y2y5h0oaUDMVTmbsBaNuZPqzjyXeAqyj4tSSRZ4CCUsmFWPLzGj5FfL3YoEZscKbyVsi41uUpUv2d1/JQM9+/hUWnLmSYlk5+fxZLZQTpiQvDosRFjNDwzen; session_token.1755778179145597822=176ea96d25c5dcb613145601f8907f0a5867757e3ffa8c3e22261394e80b2c6e; country=ca; tkbl_session=e521f736-d9ea-410a-972a-12c05ed15051' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: cross-site' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers'"""


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
    session.queue(Request("https://www.primecables.ca/", use='curl', options=OPTIONS), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(@class, "nav2020")]')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        cats1 = cat.xpath('div/div/dl')
        for cat1 in cats1:
            cat1_name = cat1.xpath('dt/a//text()').string()

            sub_cats = cat1.xpath('dd/div/div/ul/li/a')
            for sub_cat in sub_cats:
                subcat_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string()
                session.queue(Request(url, use='curl', options=OPTIONS), process_prodlist, dict(cat=name + "|" + cat1_name + "|" + subcat_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//li[contains(@class, "product-item")]//div[contains(@class, "rating-control")]/a/@href')
    for prod in prods:
        url = prod.string()
        if url:
            url = url.split('#')[0]
            session.queue(Request(url, use='curl', options=OPTIONS), process_product, dict(context, url=url))

    next_url = data.xpath('//li[@class="next"]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', options=OPTIONS), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = data.xpath('//h1[contains(@id, "product-title")]/text()').string()
    product.ssid = data.xpath('//input[contains(@id, "product_id")]/@value').string()
    product.sku = product.ssid
    product.url = context['url']
    product.category = context['cat']

    mpn = data.xpath('//span[contains(@id, "product-model")]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    prod_json = data.xpath('''//script[contains(., '"@type": "Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand')

    revs_count = data.xpath('//span[@class="of-review"]/text()').string()
    if revs_count:
        revs_count = revs_count.split()[0].strip('( )')
        if revs_count and int(revs_count) > 0:
            revs_url = product.url.replace('p-', 'reviews-')
            session.do(Request(revs_url, use='curl', options=OPTIONS), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//div[@class="review-list"]/ul/li')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.date = rev.xpath('.//div[@class="review-date"]//text()').string()

        ssid = rev.xpath('@id').string()
        if ssid:
            review.ssid = ssid.replace('review-', '')

        author = rev.xpath('.//span[@itemprop="author"]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[@class="review-num"]/span/text()').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.xpath('.//div[@class="review-thank-amount"]//text()').string()
        if hlp_yes:
            hlp_yes = hlp_yes.replace('Thanked', '').replace('for', '').strip()
            if int(hlp_yes) > 0:
                review.add_property(type='helpful_votes', value=int(hlp_yes))

        is_verified = rev.xpath('.//img[contains(@src, "verified-buyer")]').string()
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.xpath('.//div[@class="review-content-text"]/p//text()').string()
        if excerpt:
            excerpt = remove_emoji(excerpt).strip()
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url and next_url.strip(' #'):
        session.do(Request(next_url, use='curl', options=OPTIONS), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
