from agent import *
from models.products import *
from datetime import datetime
import simplejson
import re


XCAT = ["Nieuwe collectie", "Verhuur", "Ecocheque producten", "Professioneel", "Promoties", "Veilig in het verkeer", "Cadeautips", "Merken"]


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
    session.queue(Request('https://www.asadventure.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//ul[@class='as-o-main-nav']//li[contains(@class,'as-a-menu-item--menu-bar')]")
    for cat in cats:
        name = cat.xpath(".//a[contains(@data-qa, '1_level_item')]/text()").string()

        if name not in XCAT:
            subcats = cat.xpath(".//a[contains(@data-qa, '2_level_item')]")
            for subcat in subcats:
                sub_name = subcat.xpath("text()").string()
                url = subcat.xpath("@href").string()

                if sub_name not in XCAT:
                    session.queue(Request(url), process_prodlist, dict(cat=name + "|" + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[@class='as-t-product-grid__item']")
    for prod in prods:
        name = prod.xpath('.//img[@class="as-a-image"]/@alt').string()
        url = prod.xpath('.//a[contains(@class, "product-tile")]/@href').string()

        revs_count = prod.xpath(".//span[contains(@class, 'as-a-text as-a-text--subtle as-a-text--xs')]/text()").string()
        if url and revs_count and int(revs_count) > 0:
            url = url.split('?')[0]
            session.queue(Request(url), process_product, dict(context, name=name, revs_count=revs_count, url=url))

    next_url = data.xpath("//a[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[@property="og:brand"]/@content').string()

    prod_info = data.xpath("//script[contains(., 'var productInfo = ')]/text()").string()
    if prod_info:
        prod_info = simplejson.loads(prod_info.split(' = ')[-1])
        product.ssid = prod_info.get("productId")
        product.sku = product.ssid

        mpn = prod_info.get('productCode')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        url = "https://www.asadventure.com/api/aem/review/product/" + product.ssid + "?shopId=95&market=be&mainWebshop=asadventure&language=nl&anaLang=nl&ignoreLang=true&size=" + context['revs_count']
        session.do(Request(url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    data = data.content.replace("{}\r\n", "")
    if not data:
        return

    revs = simplejson.loads(data)
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('reviewId')

        date = rev.get('dateInserted')
        if date:
            review.date = str(datetime.fromtimestamp(date/1000).date())

        author_name = rev.get('customerName')
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = rev.get('score')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        pros = rev.get('reviewTextPositive')
        if pros:
            for pro in pros.splitlines():
                pro = remove_emoji(pro).strip(' +-/\n?')
                if len(pro) > 1 and not(pro.lower() == 'null' or pro.lower() == 'no' or pro.lower() == 'na'):
                    review.add_property(type='pros', value=pro)

        cons = rev.get('reviewTextNegative')
        if cons:
            for con in cons.splitlines():
                con = remove_emoji(con).strip(' +-/\n?')
                if len(con) > 1 and not(con == 'null' or con.lower() == 'no' or con.lower() == 'na'):
                    review.add_property(type='cons', value=con)

        excerpt = rev.get('reviewTitle')
        if excerpt:
            excerpt = remove_emoji(excerpt).strip()
            if len(excerpt) > 1:
                review.add_property(type="excerpt", value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page