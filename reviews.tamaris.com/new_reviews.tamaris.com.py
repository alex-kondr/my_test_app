from agent import *
from models.products import *
import simplejson
import re
import HTMLParser


h = HTMLParser.HTMLParser()


XCAT = ['Neuheiten', 'Shop By', 'Exklusiv bei Tamaris', 'Kollektionen', 'Sale', 'Aus unserer Werbung', 'Exklusiv bei uns']
DUPE_PRODS = []


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
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request('https://tamaris.com/de-CH/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[contains(@class, "navbar-nav menu-level")]/li')
    for cat in cats:
        name = cat.xpath('a//span/text()').string()

        if name and name not in XCAT:
            cats1 = cat.xpath('div/ul/li[contains(@class, "dropdown-item")]/ul/li')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a//span/text()').string().replace(' | ', '/')

                if 'Alle ' not in cat1_name:
                    subcats = cat1.xpath('div/ul/li/a[@class="dropdown-link"]')
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.xpath('.//span/text()').string()
                            url = subcat.xpath('@href').string()
                            session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                    else:
                        url = cat1.xpath('a/@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "product-tile")]')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('.//div[contains(@class, "product-name")]/text()').string()
        product.url = prod.xpath('.//a[@class="tile-link"]/@href').string()
        product.ssid = prod.xpath('@data-uuid').string()
        product.sku = prod.xpath('@data-master').string()
        product.category = context['cat']
        product.manufacturer = 'Tamaris'

        ean = prod.xpath('@data-ean').string()
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

        mpn = prod.xpath('@data-itemid').string()
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

            revs_url = 'https://cdn-ws.turnto.eu/v5/sitedata/7ow2UbXsJQJAP18site/%s/r/relatedReview/de_CH/0/10/RECENT?' % mpn
            session.queue(Request(revs_url), process_reviews, dict(product=product, mpn=mpn))

    next_url = data.xpath('//a[contains(@class, "load-more-results")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']
    if product.sku in DUPE_PRODS:
        return

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('reviews', [])
    for rev in revs:
        if rev.get('locale') != 'de_CH' and rev.get('locale') != 'de_DE':
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))
        review.date = rev.get('dateCreatedFormatted')

        author = rev.get('user', {})
        if author:
            author_name = author.get('nickName', '')
            if not author_name:
                author_name = author.get('firstName', '') + " " + author.get('lastName', '')

            author_ssid = author.get('id')
            if author_name and author_ssid:
                author_name = h.unescape(author_name).strip()
                review.authors.append(Person(name=author_name, ssid=str(author_ssid)))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.get('upVotes')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('downVotes')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_yes))

        is_verified_buyer = rev.get('purchaseDateFormatted')
        if is_verified_buyer and len(is_verified_buyer) > 2:
            review.add_property(type='is_verified_buyer', value=True)

        is_recommended = rev.get('recommended')
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        title = rev.get('title')
        excerpt = rev.get('text')
        if excerpt:
            if title:
                review.title = h.unescape(remove_emoji(title.replace('<br />', ''))).strip(' .')
        else:
            excerpt = title

        if excerpt:
            excerpt = h.unescape(remove_emoji(excerpt.replace('<br />', ''))).strip(' .')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    offset = context.get('offset', 0) + 10
    revs_cnt = revs_json.get('total')
    if revs_cnt and offset < int(revs_cnt):
        next_url = 'https://cdn-ws.turnto.eu/v5/sitedata/7ow2UbXsJQJAP18site/%s/r/relatedReview/de_CH/%s/10/RECENT?' % (context['mpn'], offset)
        session.do(Request(next_url), process_reviews, dict(context, offset=offset))

    elif product.reviews:
        session.emit(product)
        DUPE_PRODS.append(product.sku)
