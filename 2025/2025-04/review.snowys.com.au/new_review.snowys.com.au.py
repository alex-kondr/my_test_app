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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.snowys.com.au/", use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[ul[@class="home-subcategory-list"]]')
    for cat in cats:
        name = cat.xpath('a//text()').string()

        sub_cats = cat.xpath('ul[@class="home-subcategory-list"]/li')
        if sub_cats:
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a//text()').string()

                sub_cats1 = sub_cat.xpath('ul[@class="home-subsubcategory-list"]/li/a')
                if sub_cats1:
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('.//text()').string(multiple=True)
                        url = sub_cat1.xpath('@href').string()
                        session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                else:
                    url = sub_cat.xpath('a/@href').string()
                    session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name))
        else:
            url = cat.xpath('a/@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "product-item")]')
    for prod in prods:
        url = prod.xpath('.//a[@class="product-linksubarea"]/@href').string()
        ssid = prod.xpath('@data-productid').string()

        revs_cnt = prod.xpath('.//div[@class="reviewsCount"]//text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, url=url, ssid=ssid))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = data.xpath('//div[@class="product-name"]/h1/text()').string()
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = data.xpath('//div[contains(@id, "sku")]/text()').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[@class="product-name"]/h2//text()').string(multiple=True)

    mpn = data.xpath('//div[contains(@id, "mpn")]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    prod_json = data.xpath('''//script[contains(text(), '"@type": "Product"')]/text()''').string()
    if prod_json:
        ean = prod_json.split('"gtin13" : "')[-1].split('"')[0]
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_url = 'https://www.snowys.com.au/DbgReviews/ProductDetailsReviews/?pagenumber=1&productId={}&pageSize=5&orderBy=0'.format(product.ssid)
    session.do(Request(revs_url, use='curl', force_charset='utf-8'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//div[@class="product-review-item"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//span[@class="date"]/@content').string()

        author = rev.xpath('div[@class="customer-name"]/span/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[@class="rating"]/span//text()').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.xpath('.//input[@title="Upvote"]/@value').string()
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        title = rev.xpath('h4//text()').string(multiple=True)
        excerpt = rev.xpath('(p|span)//text()').string(multiple=True)
        if excerpt and len(remove_emoji(excerpt.strip(' +-*'))) > 2:
            if title:
                review.title = remove_emoji(title)
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip(' +-*')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                ssid = rev.xpath('div[contains(@class, "vote-options")]/@id').string()
                if ssid:
                    review.ssid = ssid.split('options-')[-1]
                else:
                    review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.do(Request(next_url, use='curl', force_charset='utf-8'), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
