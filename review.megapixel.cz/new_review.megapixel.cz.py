from agent import *
from models.products import *
import re


XCAT = ['Bazar', 'Akce', 'Služby', 'B2B', 'Bazar foto a video techniky a příslušenství', 'Výkup']


def serialize_text(text):
    text = re.sub(r'&([a-zA-Z]+);', lambda match: '&' + match.group(1).lower() + ';', text).replace('<br />', ' ').replace('<br/>', ' ').replace('<br/', ' ').replace("\r", "").replace("\n", "").replace('\t', '').replace('&', '&').replace('°', '°').replace('œ', 'œ').replace('í', 'í').replace('ú', 'ú').replace('“', '"').replace('£', '£').replace('"', '"').replace('à', 'à').replace('é', 'é').replace('á', 'á').replace('´', '́').replace('ã', 'ã').replace('ç', 'ç').replace('ó', 'ó').replace('€', '€').replace('ê', 'ê').replace('è', 'è').replace('’', '’').replace('”', '”').replace(' ', ' ').replace('<', '<').replace('>', '>').replace('‘', '‘').replace('–', '–').replace('ä', 'ä').replace('ß', 'ß').replace('ö', 'ö').replace('ü', 'ü').replace('â', 'â').replace('õ', 'õ').replace('ø', 'ø').replace('…', '…').replace('„', '„').replace('—', '—')
    return text


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
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request('https://www.megapixel.cz/eshop', use='curl'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[h1[contains(., "E-shop Megapixel")]]/h2')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            subcats = cat.xpath('following-sibling::section[1]//section/a')
            for subcat in subcats:
                subcat_name = subcat.xpath('.//h3/text()').string()
                url = subcat.xpath('@href').string()
                session.queue(Request(url, use='curl'), process_prodlist, dict(cat=name+'|'+subcat_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[@id="products"]//a[contains(@class, "product-box__link")]')
    for prod in prods:
        name = prod.xpath('.//h4/text()').string()
        url = prod.xpath('@href').string()

        revs_cnt = prod.xpath('.//span[@class="rating__count"]/text()').string()
        if revs_cnt:
            revs_cnt = int(revs_cnt.strip('( ×)'))
            if revs_cnt > 0:
                session.queue(Request(url, use='curl'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(@class, "paging__btn-next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//textarea[@id="product-detail-id"]/text()').string()
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[@property="og:brand"]/@content').string()

    mpn = data.xpath('//textarea[@id="product-detail-pn"]/text()').string()
    if mpn and len(mpn) > 4:
        product.add_property(type='id.manufacturer', value=mpn)

    session.do(Request(product.url+'/recenze', use='curl'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//div[contains(@class, "comment-list__item")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//p[contains(@class, "comment__author-content")]/text()[last()]').string()
        if date:
            review.date = date.split(', ')[-1].strip()

        author = rev.xpath('.//p[contains(@class, "comment__author-content")]/text()[last()]').string()
        if author:
            author = author.rsplit(', ', 1)[0].strip()
            if len(author) > 1:
                author = remove_emoji(serialize_text(author)).strip()

        grade_overall = rev.xpath('.//span[@class="sr-only"]/text()').string()
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.xpath('.//p[contains(text(), "Ověřený zákazník")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.xpath('div[@class="comment__text"]/p/text()').string(multiple=True)
        if excerpt:
            excerpt = remove_emoji(serialize_text(excerpt)).strip()
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product = context['product']
                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# load all reviews
