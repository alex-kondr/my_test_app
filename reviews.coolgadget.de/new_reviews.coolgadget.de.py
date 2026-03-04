from agent import *
from models.products import *
import re
import simplejson


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
    # session.queue(Request('https://www.coolgadget.de/collections/klapphullen-iphone', use='curl', force_charset='utf-8'), process_prodlist, dict())
    session.queue(Request('https://www.coolgadget.de/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data,context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class="main-nav"]/li')
    for cat in cats:
        name = cat.xpath('details/summary/a/text()|a/text()').string(multiple=True)

        if name:
            cats1 = cat.xpath('.//ul/li')

            if cats1:
                for cat1 in cats1:
                    cat1_name = cat1.xpath('.//a[@class="main-nav__item child-nav__item" or @class="child-nav__item main-nav__item main-nav__item-content"]//text()[not(contains(., "Neu"))]').string(multiple=True)

                    if cat1_name:
                        subcats = cat1.xpath('.//ul/li/a')
                        if subcats:
                            for subcat in subcats:
                                subcat_name = subcat.xpath('text()').string()
                                url = subcat.xpath('@href').string()
                                session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                        else:
                            url = cat1.xpath('.//a[@class="main-nav__item child-nav__item" or @class="child-nav__item main-nav__item main-nav__item-content"]/@href').string()
                            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name+'|'+cat1_name))
            else:
                url = cat.xpath('details/summary/a/@href|a/@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "card__info-inner")]')
    for prod in prods:
        name = prod.xpath('p/a[contains(@class, "card-link")]/text()').string()
        url = prod.xpath('p/a[contains(@class, "card-link")]/@href').string()

        revs_cnt = prod.xpath('.//div[contains(@class, "rating__count")]/text()').string()
        if revs_cnt and int(revs_cnt.strip('( )')) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div/@data-id').string()
    product.sku = product.ssid
    product.category = context['cat']

    prod_json = data.xpath('''//script[contains(., '"gtin": ')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('brand', {}).get('name')

        mpn = prod_json.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('gtin')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_url = 'https://api.judge.me/reviews/reviews_for_widget?url=df6282-d9.myshopify.com&shop_domain=df6282-d9.myshopify.com&platform=shopify&page=1&per_page=5&product_id=' + product.ssid
    session.do(Request(revs_url, use='curl', force_charset='utf-8'), process_reviews, dict(product=product))


def process_reviews(data,context, session):
    strip_namespace(data)

    product = context['product']

    revs_json = simplejson.loads(data.content)

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
