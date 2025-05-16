from agent import *
from models.products import *
import re


XCAT = ['Software', 'Noten', 'SALE', 'B-Stock', 'Retouren', 'Gutscheine', 'Schlagzeug News', 'Newsblog', 'Licht-Videos', 'Frequenzbereiche Europa', 'Gitarre & Bass', 'PA Equipment']


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
                               u"\u0081"  # additional character
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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.browser.use_new_parser = True
    session.queue(Request('https://www.musicstore.de/de_DE/EUR', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('(//ul[contains(@class, "kor-mainNavigation")])[1]/li//a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        if name not in XCAT:
            session.do(Request(url, use='curl', force_charset='utf-8', max_age=0), process_subcategory, dict(cat=name))


def process_subcategory(data, context, session):
    strip_namespace(data)

    subcats = data.xpath('//div[contains(@class, "category-container-tile")]')
    if not subcats:
        process_prodlist(data, context, session)
        return

    for subcat in subcats:
        name = subcat.xpath('.//div[@class="name"]/span/text()').string()
        url = subcat.xpath('a/@href').string()
        if name not in XCAT and 'youtube' not in url:
            session.do(Request(url+'?PageSize=90', use='curl', force_charset='utf-8', max_age=0), process_subcategory, dict(cat=context['cat']+'|'+name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="tile-product-wrapper"]')
    for prod in prods:
        name = prod.xpath('.//a[contains(@class, "name kor-product")]/span/@title').string()
        url = prod.xpath('.//a[contains(@class, "name kor-product")]/@href').string()

        revs_cnt = prod.xpath('.//div/span[@class="count"]/text()').string()
        if revs_cnt:
            revs_cnt = revs_cnt.strip('( )').replace('.', '')
            if int(revs_cnt) > 0:
                session.do(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url, revs_cnt=int(revs_cnt)))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = remove_emoji(context['name']).strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']
    product.manufacturer = data.xpath('//span[@class="brand"]/text()').string()

    mpn = data.xpath('//span[@class="artnr"]/span/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//div/@data-loadbee-gtin').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    revs_id = data.xpath('//li/a[@class="ReviewPage"]/@data-href').string()
    if revs_id:
        revs_id = revs_id.split('PageableID=')[-1].split('&SKU')[0]
        revs_url = 'https://www.musicstore.de/INTERSHOP/web/WFS/MusicStore-MusicStoreShop-Site/de_DE/-/EUR/ViewProductReview-Paging?PageNumber=1&PageSize=5&PageableID={}&SKU={}'.format(revs_id, product.ssid)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, revs_id=revs_id))
    else:
        context['product'] = product
        process_reviews(data, context, session)


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//div[@class="review-item-box"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('.//span/@data-reviewid').string()
        review.date = rev.xpath('.//span[@class="review-creation-date"]/text()').string()

        author = rev.xpath('.//span[@class="review-author"]/text()').string()
        if author:
            author = remove_emoji(author).strip()
            if author:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//div[@class="ish-reviewItem-header"]/i[contains(@class, "star orange")])')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=grade_overall, best=5.0))

        grades = rev.xpath('.//ul[contains(@class, "review-attribute")]/li')
        for grade in grades:
            grade_name = grade.xpath('span/text()').string()
            grade_value = grade.xpath('count(.//i[contains(@class, "star orange")])')
            review.grades.append(Grade(name=grade_name, value=grade_value, best=5.0))

        hlp = rev.xpath('.//div/p[@class="nopad"][contains(., " von ")]/text()').string()
        if hlp:
            hlp_yes = hlp.split(' von ')[0].strip().replace('.', '')
            review.add_property(type='helpful_votes', value=int(hlp_yes))

            hlp_total = hlp.split(' von ')[-1].split()[0].strip().replace('.', '')
            review.add_property(type='not_helpful_votes', value=int(hlp_total) - int(hlp_yes))

        title = rev.xpath('.//div/h3/text()').string()
        excerpt = rev.xpath('.//div[contains(@class, "review-text")]/p//text()').string(multiple=True)
        if excerpt and len(remove_emoji(excerpt).strip()) > 1:
            if title:
                review.title = remove_emoji(title).strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip()
            if len(excerpt) > 1:
                review.add_property(type="excerpt", value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt'] and context.get('revs_id'):
        next_page = context.get('next_page', 1) + 1
        revs_url = 'https://www.musicstore.de/INTERSHOP/web/WFS/MusicStore-MusicStoreShop-Site/de_DE/-/EUR/ViewProductReview-Paging?PageNumber={page}&PageSize=5&PageableID={revs_id}&SKU={ssid}'.format(page=next_page, revs_id=context['revs_id'], ssid=product.ssid)
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
