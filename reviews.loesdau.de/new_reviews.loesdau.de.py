from agent import *
from models.products import *
import re


XCAT = ['Gutschein', 'Neu', 'Sale', 'Marken', 'Pferdesporthäuser', 'Informationen']


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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.loesdau.de/', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class="level1"]/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('ul[@class="level2"]/li')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a/text()').string()

                if cat1_name not in XCAT:
                    subcats = cat1.xpath('ul[@class="level3"]/li/a')
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.xpath('text()').string()
                            url = subcat.xpath('@href').string()
                            session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                    else:
                        url = cat1.xpath('a/@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "product  tileproduct")]')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('.//h2//span[@itemprop="name"]/text()').string()
        product.url = prod.xpath('.//h2/a[@class="title link"]/@href').string().split('?')[0]
        product.ssid = product.url.split('/')[-1].replace('.html', '')
        product.sku = prod.xpath('@data-rel').string()
        product.category = context['cat']
        product.manufacturer = prod.xpath('.//div[@class="brand"]/meta/@content').string()

        revs_url = "https://www.loesdau.de/bewertungen/" + product.ssid + '.html'
        session.queue(Request(revs_url), process_reviews, dict(product=product, revs_url=revs_url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//div[@class="rating"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['revs_url']

        date = rev.xpath('.//p[@class="date SMALL"]/text()[contains(., " am ")]').string()
        if date:
            review.date = date.split('am ')[-1].strip(' -')

        author = rev.xpath('.//p[@class="date SMALL"]/b/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[@class="stars"]/div/@title').string()
        if grade_overall:
            grade_overall = grade_overall.split('/')[0].strip()
            if grade_overall.isdigit() and float(grade_overall) > 0:
                review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//span[@class="verified-rating"]/text()').string()
        if is_verified and is_verified == 'bestätigter Kauf':
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.xpath('.//p[not(@class)]/span/text()').string(multiple=True)
        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').replace('\r', '').strip(' .+-*')
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    next_url = data.xpath('//li[@class="next"]/a/@href').string()
    if next_url:
        next_url = next_url.split('#')[0]
        session.do(Request(next_url), process_reviews, dict(revs_url=next_url, product=product))

    elif product.reviews:
        session.emit(product)
