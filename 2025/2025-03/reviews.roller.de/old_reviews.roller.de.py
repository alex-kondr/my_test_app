from agent import *
from models.products import *
import simplejson
from datetime import datetime
import re


XCAT = ['Wohnideen', 'SALE', 'Marken', 'Prospekte', 'Gutscheine', 'Wohnbereiche', 'Küchenstudio', 'Planung und Beratung']
OPTIONS = "-H 'authority: www.roller.de' -H 'accept-language: uk,en;q=0.9,en-GB;q=0.8,en-US;q=0.7' -H 'cache-control: no-cache' -H 'pragma: no-cache' -H 'referer: https://www.roller.de/' -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0' --compressed"


def serialize_text(text):
    text = re.sub(r'&([a-zA-Z]+);', lambda match: '&' + match.group(1).lower() + ';', text).replace('<br />', ' ').replace('<br/>', ' ').replace('<br/', ' ').replace("\r", "").replace("\n", "").replace('\t', '').replace('&amp;', '&').replace('&deg;', '°').replace('&oelig;', 'œ').replace('&iacute;', 'í').replace('&uacute;', 'ú').replace('&ldquo;', '"').replace('&pound;', '£').replace('&quot;', '"').replace('&agrave;', 'à').replace('&eacute;', 'é').replace('&aacute;', 'á').replace('&acute;', '́').replace('&atilde;', 'ã').replace('&ccedil;', 'ç').replace('&oacute;', 'ó').replace('&euro;', '€').replace('&ecirc;', 'ê').replace('&egrave;', 'è').replace('&rsquo;', '’').replace('&rdquo;', '”').replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&lsquo;', '‘').replace('&ndash;', '–').replace('&auml;', 'ä').replace('&szlig;', 'ß').replace('&ouml;', 'ö').replace('&uuml;', 'ü').replace('&acirc;', 'â').replace('&otilde;', 'õ').replace('&oslash;', 'ø').replace('&hellip;', '…').replace('&bdquo;', '„').replace('&mdash;', '—')
    return text


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
                               u"&#\d+;"  # HTML entities
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.roller.de/wohnbereiche/', max_age=0), process_catlist, dict())   # Home-page doesn't have 'id="mainNav"'


def process_catlist(data, context, session):
    cats1 = data.xpath('//div[@id="mainNav"]/div')
    for cat1 in cats1:
        name1 = cat1.xpath('a/text()').string()

        if name1 not in XCAT:
            cats2 = cat1.xpath('div//div[@class="h3"]/a')
            for cat2 in cats2:
                name2 = cat2.xpath('text()').string()
                url = cat2.xpath('@href').string()

                if name2 not in XCAT:
                    session.queue(Request(url, max_age=0), process_subcategory, dict(cat=name1+'|'+name2))


def process_subcategory(data, context, session):
    subcats = data.xpath('//ul[contains(@class, "Cat-menu")]/li/a')
    for subcat in subcats:
        name = subcat.xpath('span/text()').string()
        url = subcat.xpath("@href").string()
        session.queue(Request(url+'results?page=0&pageSize=108', max_age=0), process_prodlist, dict(cat=context['cat']+'|'+name, cat_url=url))


def process_prodlist(data, context, session):
    prodlist_json = simplejson.loads(data.content)

    prods = prodlist_json.get('results', [])
    for prod in prods:
        product = Product()
        product.name = prod['name']
        product.url = 'https://www.roller.de' + prod['url']
        product.manufacturer = prod.get('manufacturer')
        product.category = context['cat'].strip('|')
        product.ssid = prod.get('productCode')
        product.sku = product.ssid

        revs_cnt = prod.get('numberOfReviews')
        if int(revs_cnt) > 0:
            session.do(Request(product.url+'/reviews.json?page=0', max_age=0), process_reviews, dict(product=product))

    max_page = context.get('max_page', prodlist_json.get('pagination', {}).get('numberOfPages'))
    next_page = context.get('page', 0) + 1
    if max_page >= next_page:
        prods_url = context['cat_url'] + 'results?page={}'.format(next_page)
        session.queue(Request(prods_url, max_age=0), process_prodlist, dict(context, page=next_page, max_page=max_page))


def process_reviews(data, context, session):
    product = context['product']

    resp = simplejson.loads(data.content)

    revs = resp['reviews'].get('results', [])
    for rev in revs:
        review = Review()
        review.ssid = str(rev['id'])
        review.type = 'user'
        review.url = product.url

        title = rev.get('headline')
        if title:
            review.title = serialize_text(title)

        date = rev.get('reviewDate')
        if date:
            review.date = datetime.utcfromtimestamp(date / 1000).strftime('%Y-%m-%d')

        author = rev.get('alias')   # No authors
        if author:
            author = serialize_text(author)
            review.authors.append(Person(name=author, ssid=author))

        grade = rev.get('rating')
        if grade:
            review.grades.append(Grade(type='overall', value=float(grade), best=5.0))

        excerpt = rev.get('comment')
        if excerpt:
            excerpt = remove_emoji(serialize_text(excerpt)).strip()
            if excerpt:
                review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

                product.reviews.append(review)

    max_page = context.get('max_page', resp['reviews'].get('pagination', {}).get('numberOfPages'))
    next_page = context.get('page', 0) + 1
    if max_page >= next_page:
        revs_url = product.url + '/reviews.json?page={}'.format(next_page)
        session.do(Request(revs_url, max_age=0), process_reviews, dict(context, page=next_page, max_page=max_page))
    elif product.reviews:
        session.emit(product)
