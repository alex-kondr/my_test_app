from agent import *
from models.products import *
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
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.coolgadget.de/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data,context, session):
    strip_namespace(data)
    cats = data.xpath('//a[contains(@class, "category-link")]')
    for cat in cats:
        name = cat.xpath('text()').string(multiple=True)
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(@class, "level-1")]/a[contains(@class, "item-link")]')
    for cat in cats:
        name = cat.xpath('span[contains(@class, "title")]/text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_subcatlist, dict(cat=context['cat'] + '|' + name))


def process_subcatlist(data, context, session):
    strip_namespace(data)
    sub_cats = data.xpath('//li[contains(@class, "level-2")]/a[contains(@class, "item-link")]')
    for sub_cat in sub_cats:
        sub_name = sub_cat.xpath('span[contains(@class, "title")]/text()').string()
        url = sub_cat.xpath('@href').string()
        session.queue(Request(url + '?items=100', use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + sub_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//article[contains(@class, "item")]/div[@data-id]')
    for prod in prods:
        name = prod.xpath('div[contains(@class, "title")]/a/text()').string()
        url = prod.xpath('div[contains(@class, "title")]/a/@href').string()

        revs_cnt = prod.xpath('.//span[@class="count"]/text()').string()
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//li[contains(@class, "next-page")]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@id="ArticleId"]/@value').string()
    product.sku = data.xpath('//span[@itemprop="sku"]/text()').string()
    product.category = context['cat'].replace('weitere Modelle', '').replace('||', '|').strip()
    product.manufacturer = data.xpath('(//label[contains(., "Marke")]/following-sibling::span)[1]/text()').string()

    mpn = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//meta[@itemprop="gtin"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs_url = data.xpath('//div[contains(@class, "show-all-reviews")]/a/@href').string()
    session.do(Request(revs_url, use='curl', force_charset='utf-8'), process_reviews, dict(product=product, url=revs_url))


def process_reviews(data,context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//div[@data-refresh-id]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['url']
        review.ssid = rev.xpath('@data-review-id').string()

        date_author = rev.xpath('.//div[contains(@class, "author")]/text()').string(multiple=True)
        if date_author:
            review.date = date_author.rsplit(' ', 1)[0].split()[-1]

            author = date_author.split(' verfasst ')[0]
            review.authors.append(Person(name=author, ssid=author))

        # no grade

        is_verified_buyer = rev.xpath('.//span[contains(., "Verifizierter Kauf")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes_no = rev.xpath('.//small[@class="grey"]/text()').string()
        if hlp_yes_no:
            hlp_yes = hlp_yes_no.split(' von ')[0]
            hlp_no = hlp_yes_no.split(' von ')[1].split()[0]

            if hlp_yes and hlp_yes.isdigit() and int(hlp_yes) > 0:
                review.add_property(type='helpful_votes', value=int(hlp_yes))

            if hlp_no and hlp_no.isdigit() and int(hlp_no) > 0:
                review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.xpath('.//h4[contains(@class, "item-title")]//text()').string(multiple=True)
        excerpt = rev.xpath('.//div[contains(@class, "item-comment")]//text()').string(multiple=True)
        if excerpt and len(remove_emoji(excerpt).strip(' .+-')) > 2:
            if title:
                review.title = remove_emoji(title).strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip(' +-')
            if '...' in excerpt:
                excerpt = excerpt.strip(' .')

            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
