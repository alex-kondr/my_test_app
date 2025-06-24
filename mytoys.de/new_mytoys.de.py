from agent import *
from models.products import *
import simplejson


XCAT = ['Inspiration', 'Marken', '%Sale%', '% Sale', 'Aktionen', 'Neuheiten', 'Beratung', 'Inspiration & Themen', 'Premium-Marken', "Levi's®", 'Tommy Hilfiger', 'Nachhaltige Artikel', 'adidas', 'Nike', 'LeGer Home by Lena Gercke', '']


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
    session.queue(Request('https://www.otto.de/', use='curl', force_charset='utf-8'), process_frontpage, dict())
    session.queue(Request('https://www.otto.de/damen/', use='curl', force_charset='utf-8'), process_catlist, dict(cat='Damen'))


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[contains(@class, "global-navigation")]/li[contains(@class, "item-element")]//a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_catlist, dict(cat=name))


def process_catlist(data,context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="nav_local-category"]')
    for cat in cats:
        name = cat.xpath('.//li[@class="nav_local-link nav_link-headline"]/a/span[@class="nav_link-title"]/text()').string()

        if name and name not in XCAT:
            sub_cats = cat.xpath('.//li[@class="nav_local-link "]/a')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('span[@class="nav_link-title"]/text()').string()
                url = sub_cat.xpath('@href').string()

                if not sub_name.lower().startswith('alle'):
                    if '/?' in url:
                        prods_url = url + '&sortiertnach=bewertung'
                    else:
                        prods_url = url + '?sortiertnach=bewertung'

                    session.queue(Request(prods_url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + name + '|' + sub_name, cat_url=url))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//article[contains(@class, "product")]')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('.//p[contains(@class, "find_tile__name")]/text()').string()
        product.url = prod.xpath('.//a/@href').string().split('#')[0]
        product.ssid = prod.xpath('@data-product-id').string()
        product.sku = product.ssid
        product.category = context['cat']
        product.manufacturer = prod.xpath('.//p[contains(@class, "tile__brand")]/text()').string()

        mpn = prod.xpath('@data-article-number').string()
        if mpn and mpn != product.ssid:
            product.add_property(type='id.manufacturer', value=mpn)

        prod_json = prod.xpath('.//script[@type="application/ld+json"]/text()').string()
        if prod_json and simplejson.loads(prod_json).get('aggregateRating', {}).get('reviewCount', 0) > 0:
            revs_url = 'https://www.otto.de/kundenbewertungen/{}/'.format(product.ssid)
            session.do(Request(revs_url, use='curl', force_charset='utf-8'), process_reviews, dict(product=product))
        else:
            return

    prods_cnt = data.xpath('//span[contains(@class, "itemCount")]/text()').string()
    if prods_cnt:
        prods_cnt = int(prods_cnt.replace('Produkte', '').replace('.', '').strip())
        offset = context.get('offset', 0) + 120
        if offset < prods_cnt:
            if '/?' in context['cat_url']:
                next_url = context['cat_url'] + '&l=gp&o={}&sortiertnach=bewertung'
            else:
                next_url = context['cat_url'] + '?l=gp&o={}&sortiertnach=bewertung'

            session.queue(Request(next_url.format(offset), use='curl', force_charset='utf-8'), process_prodlist, dict(context, prods_cnt=prods_cnt, offset=offset))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//div[contains(@id, "review-list")]/div[contains(@class, "item-content")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@data-review-id').string()

        date = rev.xpath('.//span[contains(@class, "item__customer")]/text()[last()] ').string()
        if date:
            review.date = date.split(' am ')[-1].strip()

        author = rev.xpath('.//span[contains(@class, "item__customer")]/b/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('@data-rating').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.xpath('.//span[contains(., "Verifizierter Kauf")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.xpath('.//span[contains(@class, "helpfulVoteCount")]/text()').string()
        if hlp_yes:
            hlp_yes = int(hlp_yes)
            if hlp_yes:
                review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_total = rev.xpath('.//span[contains(@class, "helpfulVoteTotalCount")]/text()').string()
        if hlp_total:
            hlp_total = int(hlp_total)
            if not hlp_yes:
                hlp_yes = 0

            hlp_no = hlp_total - hlp_yes
            if hlp_no:
                review.add_property(type='not_helpful_votes', value=hlp_no)

        title = rev.xpath('.//h3[contains(@class, "item__title")]/text()').string()
        excerpt = rev.xpath('.//span[contains(@class, "reviewText")]//text()').string(multiple=True)
        if excerpt and len(remove_emoji(excerpt).replace('\n', '').replace('\t', '').strip(' +-*.;•–')) > 1:
            if title:
                review.title = remove_emoji(title).replace('\n', '').replace('\t', '').strip(' +-*.;•–')
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).replace('\n', '').replace('\t', '').strip(' +-*.;•–')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
