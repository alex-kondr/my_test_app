from agent import *
from models.products import *
import simplejson
import re


XCAT = ["Nieuwe collectie", "Nieuwe outdoorcollectie", "Nieuwe fashioncollectie", "Verhuur", "Ecocheque producten", "Professioneel", "Promoties", "Veilig in het verkeer", "Cadeautips", "Merken"]


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
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.asadventure.com/nl.html', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, contenxt, session):
    cats = data.xpath('//div[contains(@class, "category-flyout__menu")]')
    for cat in cats:
        name = cat.xpath('div[contains(@class, "title")]/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('ul[contains(@class, "category-flyout__menu")]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('li[contains(@class, "menu-item")]/a/text()').string()

                if sub_name not in XCAT:
                    sub_cats1 = sub_cat.xpath('li[not(contains(@class, "menu-item"))]/a')

                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('text()').string()
                        url = sub_cat1.xpath('@href').string()

                        if sub_name1 not in XCAT:
                            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                    else:
                        url = sub_cat.xpath('li[contains(@class, "menu-item")]/a/@href').string()
                        session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-tile--vertical")]')
    for prod in prods:
        url = prod.xpath('span/a/@href').string().split('?')[0]

        revs_cnt = prod.xpath('.//div[contains(@class, "rating")]//span[contains(@class, "subtle")]/text()').string()
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = data.xpath('//h1[contains(@class, "title")]//span[contains(@class, "title")]/text()').string()
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = data.xpath('//h1[contains(@class, "title")]//a/text()').string()

    mpn = product.url.split('-')[-1].replace('.html', '')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    prod_info = data.xpath("//script[contains(., 'var productInfo = ')]/text()").string()
    if prod_info:
        prod_info = simplejson.loads(prod_info.split(' = ')[-1])
        product.ssid = prod_info.get("productId")
        product.sku = product.ssid

    revs = data.xpath('//div[div/span[contains(., "Reviews")] and contains(@class, "content--modal")]//div[@class="as-t-box"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date_author = rev.xpath('.//div[contains(@class, "text--subtle")]/span/text()').string()
        if date_author:
            review.date = date_author.rsplit(' ', 1)[-1]

            author = date_author.rsplit(',')[0].split(' door ')[-1].strip()
            if author:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//span[contains(@class, "rating-item--full")])')
        if grade_overall and grade_overall > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        pros = rev.xpath('.//li[.//span[contains(@class, "positive")]]//div//span//text()').string(multiple=True, normalize_space=False)
        if pros:
            if '\n' in pros:
                pros = pros.split('\n')
            elif '.' in pros:
                pros = pros.split('.')
            elif ';' in pros:
                pros = pros.split(';')
            else:
                pros = [pros]

            for pro in pros:
                pro = remove_emoji(pro).strip(' +-/\n?')
                if len(pro) > 1 and not(pro.lower() == 'null' or pro.lower() == 'no' or pro.lower() == 'na'):
                    review.add_property(type='pros', value=pro)

        cons = rev.xpath('.//li[.//span[contains(@class, "negative")]]//div//span//text()').string(multiple=True, normalize_space=False)
        if cons:
            if '\n' in cons:
                cons = cons.split('\n')
            elif '.' in cons:
                cons = cons.split('.')
            elif ';' in cons:
                cons = cons.split(';')
            else:
                cons = [cons]

            for con in cons:
                con = remove_emoji(con).strip(' +-/\n?')
                if len(con) > 1 and not(con == 'null' or con.lower() == 'no' or con.lower() == 'na'):
                    review.add_property(type='cons', value=con)

        excerpt = rev.xpath('.//h2//text()').string(multiple=True)
        if excerpt:
            excerpt = remove_emoji(excerpt).strip()
            if len(excerpt) > 1:
                review.add_property(type="excerpt", value=excerpt)

                review.ssid = review.digest() if date_author and author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
