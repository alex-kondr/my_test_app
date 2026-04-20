from agent import *
from models.products import *
import simplejson
import urllib
import HTMLParser
import re


h = HTMLParser.HTMLParser()


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
    session.queue(Request('https://www.monsternotebook.com.tr/laptop/', max_age=0), process_category, dict(cat='Laptoplar'))
    session.queue(Request('https://www.monsternotebook.com.tr/masaustu-bilgisayarlar/', max_age=0), process_category, dict(cat='Masaüstü Bilgisayarlar'))
    session.queue(Request('https://www.monsternotebook.com.tr/aksesuarlar/', max_age=0), process_category, dict(cat='Aksesuarlar'))


def process_category(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[contains(@class, "category-accordion")]/li/ul/li')
    for cat in cats:
        name = cat.xpath('div/a/text()').string().split(' (')[0].strip()

        cats1 = cat.xpath('ul/li')
        for cat1 in cats1:
            cat1_name = cat1.xpath('div/a/text()').string().split(' (')[0].strip()

            subcats = cat1.xpath('ul/li//a')
            if subcats:
                for subcat in subcats:
                    subcat_name = subcat.xpath('text()').string().split(' (')[0].strip()
                    url = subcat.xpath('@href').string()
                    session.queue(Request(url, max_age=0), process_prodlist, dict(cat=context['cat']+'|'+name+'|'+cat1_name+'|'+subcat_name))

            else:
                url = cat1.xpath('div/a/@href').string()
                session.queue(Request(url, max_age=0), process_prodlist, dict(cat=context['cat']+'|'+name+'|'+cat1_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//ul[contains(@class, "product-list")]/li[contains(@class, "ems-prd")]')
    for prod in prods:
        name = prod.xpath('.//h3[contains(@class, "product_names_box")]/text()').string(multiple=True).strip()
        ssid = prod.xpath('@data-product-id').string()
        url = prod.xpath('div/a/@href').string()

        revs_cnt = prod.xpath('.//div[contains(@class, "card-rating")]/div[contains(@class, "text")]/text()').string()
        if revs_cnt:
            revs_cnt = int(revs_cnt.split(' (')[-1].strip(' )'))
            if revs_cnt > 0:
                session.queue(Request(url, max_age=0), process_product, dict(context, name=name, ssid=ssid, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = data.xpath('//input[@id="productSKUData"]/@value').string()
    product.category = context['cat']
    product.manufacturer = 'Monster Notebook'

    mpn = data.xpath('//script[contains(., "item_barebone")]/text()').string()
    if mpn:
        mpn = mpn.split('item_barebone": "')[-1].split('"', 1)[0].strip()
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

    tags = data.xpath('//div/@data-tags').string()
    if tags:
        tags = tags.split('|')
        parameters = simplejson.dumps(dict(
            ExternalId=product.ssid,
            ContentTypeId="82",
            PageSize="6",
            CurrentPage=1,
            Tags=tags
        ), )
        revs_url = 'https://www.monsternotebook.com.tr/tr/Widget/Get/ProductComments?parameters=' + urllib.quote(parameters)
        session.do(Request(revs_url, max_age=0), process_reviews, dict(product=product, tags=tags))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//div[contains(@class, " comments ")]/div')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@data-id').string()
        review.date = rev.xpath('.//div[contains(@class, "ps-5")]/text()').string()

        author = rev.xpath('.//div[contains(@class, "pe-5")]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[@class="card-rating-current"]/@style').string()
        if grade_overall:
            grade_overall = grade_overall.split(': ')[-1].strip(' ;')
            if grade_overall.isdigit() and int(grade_overall) > 0:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.xpath('.//div/a[@rel="positive"]/span/text()').string()
        if hlp_yes and hlp_yes.isdigit() and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//div/a[@rel="negative"]/span/text()').string()
        if hlp_no and hlp_no.isdigit() and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.xpath('.//div[contains(@class, "card-rating")]/div[contains(@class, "fs")]/text()').string(multiple=True)
        excerpt = rev.xpath('.//p[@data-fulltext]//text()').string(multiple=True)
        if excerpt and len(h.unescape(remove_emoji(excerpt)).strip(' *,')) > 2:
            if title:
                review.title = h.unescape(remove_emoji(title)).strip(' ,*')
        else:
            excerpt = title

        if excerpt:
            excerpt = h.unescape(remove_emoji(excerpt)).strip(' *,')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 6
    revs_cnt = context.get('revs_cnt', data.xpath('//div[@id="commentSummary"]//div[contains(@class, "fs-14")]/text()').string().split()[0])
    if offset < int(revs_cnt):
        next_page = context.get('page', 1) + 1
        tags = context['tags']
        parameters = simplejson.dumps(dict(
            ExternalId=product.ssid,
            ContentTypeId="82",
            PageSize="6",
            CurrentPage=str(next_page),
            Tags=tags
        ))
        next_url = 'https://www.monsternotebook.com.tr/tr/Widget/Get/ProductComments?parameters=' + urllib.quote(parameters)
        session.do(Request(next_url, max_age=0), process_reviews, dict(context, offset=offset, page=next_page, revs_cnt=revs_cnt))

    elif product.reviews:
        session.emit(product)
