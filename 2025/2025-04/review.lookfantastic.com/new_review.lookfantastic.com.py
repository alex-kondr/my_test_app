from agent import *
from models.products import *


XCAT = ['Summer Shop', 'New In', 'Brands', 'Beauty Box', 'Offers', 'Gifting', 'Luxury', 'Blog', 'Trending', 'Top Brands', 'Shop by Price']


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
    session.queue(Request('https://www.lookfantastic.com/', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data,context, session):
    cats = data.xpath('//div[@class="group flex"]')
    for cat in cats:
        name = cat.xpath('.//p[contains(@class, "tracking-widest")]/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('.//div[@class="sub-nav-item" and .//p]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('.//p[contains(@class, "text")]/text()').string()

                if sub_name not in XCAT:
                    sub_name = '|' + sub_name if 'Shop by' not in sub_name else ''
                    sub_cats1 = sub_cat.xpath('.//div[contains(@class, "sub-nav")]/a')
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('text()').string()
                        url = sub_cat1.xpath('@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat = name + sub_name + '|' + sub_name1))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-data")]')
    for prod in prods:
        name = prod.xpath('a/text()').string()
        url = prod.xpath('a/@href').string()

        rev_cnt = prod.xpath('.//div[contains(@class, "reviews")]/p[not(@class)]/text()').string()
        if rev_cnt and int(rev_cnt) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@data-hasmore="true"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[h1[@id="product-title"]]/a/text()').string()

    context['product'] = product

    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@id="review-wrapper"]/div')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//time/@datetime').string()

        author = rev.xpath('.//p[time]/text()').string(multiple=True)
        if author:
            author = author.split(' by ')[-1].strip()
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[contains(@class, "rating")]/p/text()').string()
        if grade_overall:
            grade_overall = grade_overall.split()[0]
            if grade_overall and grade_overall.isdigit():
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.xpath('.//p[contains(., "Verified Purchase")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.xpath('.//button[@data-upvote]/text()').string(multiple=True)
        if hlp_yes:
            hlp_yes = hlp_yes.split('(')[-1].strip('( )')
            if hlp_yes and hlp_yes.isdigit() and int(hlp_yes) > 0:
                review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//button[@data-downvote]/text()').string(multiple=True)
        if hlp_no:
            hlp_no = hlp_no.split('(')[-1].strip('( )')
            if hlp_no and hlp_no.isdigit() and int(hlp_no) > 0:
                review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.xpath('.//h4/text()').string()
        excerpt = rev.xpath('.//p[not(@class)]//text()').string(multiple=True)
        if excerpt and len(remove_emoji(excerpt)) > 2:
            if title:
                review.title = remove_emoji(title).strip()
        else:
            excerpt = title

        if excerpt:
            exceprt = remove_emoji(excerpt).strip()
            if len(exceprt) > 2:
                review.add_property(type='excerpt', value=exceprt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    next_url = data.xpath('//a[@data-hasmore="true"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
