from agent import *
from models.products import *
import re
import simplejson


XCAT = ['Alle Marken']


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
    # url= 'https://www.runnersworld.de/laufhelden/huawei-watch-gt-runner-2-mit-50-euro-laufheldenrabatt/'
    # session.queue(Request(url), process_review, dict(cat='cat', url=url, title='title'))
    session.queue(Request('https://www.runnersworld.de/ausruestung/'), process_catlist, dict())


def process_catlist(data, context, session):
    try:
        cats_json = simplejson.loads(data.xpath('//script[@id="__NEXT_DATA__"]/text()').string()).get('props', {}).get('pageProps', {}).get('pageData', {}).get('data', {}).get('header', [{}])[-1].get('basicNav', [{}])
    except:
        return

    for subcats in cats_json:
        if subcats.get('label').strip() == u'Schuhe\xa0& Ausr\xfcstung':
            subcats = subcats.get('children', [])
            for subcat in subcats:
                subcat_name = subcat.get('label')
                url = subcat.get('url')

                if subcat_name not in XCAT:
                    session.queue(Request(url), process_revlist, dict(cat='Schuhe & Ausrüstung|'+subcat_name, cat_url=url))

            return


def process_revlist(data, context, session):
    try:
        revs_json = simplejson.loads(data.xpath('//script[@id="__NEXT_DATA__"]/text()').string()).get('props', {}).get('pageProps', {}).get('pageData', {}).get('data', {}).get('mobile', [{}])
    except:
        revs_json = []

    for revs in revs_json:
        if revs.get('title', '').strip() == 'Rubrik-Liste':
            for rev in revs.get('data', []):
                title = rev.get('title')
                url = rev.get('url')
                session.queue(Request(url), process_review, dict(context, title=title, url=url))

            context['revs_cnt'] = context.get('revs_cnt', revs.get('pagination', {}).get('total', 0))
            break

    offset = context.get('offset', 0) + 25
    if offset < int(context.get('revs_cnt', 0)):
        next_page = context.get('page', 1) + 1
        next_url = context['cat_url'] + 'seite/{}/'.format(next_page)
        session.queue(Request(next_url), process_revlist, dict(context, page=next_page, offset=offset))


def process_review(data, context, session):
    try:
        revdata_json = simplejson.loads(data.xpath('//script[@id="__NEXT_DATA__"]/text()').string()).get('props', {}).get('pageProps', {}).get('pageData', {}).get('data', {}).get('mobile', [{}])
    except:
        return

    rev_json = {}
    for rev_json in revdata_json:
        if rev_json.get('id') == 'article.text':
            rev_json = rev_json.get('data', {})
            break

    new_data = '<div>'
    for text in rev_json.get('text', []):
        if isinstance(text, unicode):
            new_data += text

    new_data += '</div>'
    new_data = data.parse_fragment(new_data)

    product = Product()
    product.name = context['title'].replace(' im Test', '').replace('Im Test: ', '').replace(' im Praxistest', '').replace(' im ersten Test', '').replace(' im Dauertest', '').strip()
    product.ssid = str(rev_json.get('_id'))
    product.category = context['cat']

    product.url = new_data.xpath('//p[contains(., "Hier bestellen:")]//a/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = rev_json.get('date')
    if date:
        review.date = date.split('T')[0]

    authors = rev_json.get('author')
    if authors:
        for author in authors:
            author_name = author.get('firstName', '') + ' ' + author.get('lastName', '')
            author_ssid = str(author.get('_id'))
            author_url = author.get('url')

            if author_name and author_url:
                author_name = author_name.strip(' ,.')
                review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))

            elif author_name and len(author_name.strip(' ,.')) > 1:
                author_name = author_name.strip(' ,.')
                review.authors.append(Person(name=author_name, ssid=author_name))

            else:
                author = author.get('brief')
                if author_name and len(author_name.strip(' ,.')) > 1:
                    review.authors.append(Person(name=author_name, ssid=author_name))

    pros = new_data.xpath('//h3[contains(., "Positiv")]/following::p[contains(., "✅")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–✅')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = new_data.xpath('//h3[contains(., "Negativ")]/following::p[regexp:test(., "❌|⛔️")]//text()')
    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–❌⛔️')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = rev_json.get('intro')
    if summary:
        summary = remove_emoji(summary).strip()
        review.add_property(type='summary', value=summary)

    excerpt = new_data.xpath('//div/p[not(@class or regexp:test(., "Hier bestellen:|✅|❌|⛔️|Preis:|Fazit") or preceding::h3[regexp:test(., "Fazit|Die wichtigsten Daten|Die Plus- und Minuspunkte|Vor- und Nachteile")] or preceding::p[strong[contains(., "Fazit")]])]//text()').string(multiple=True)
    if excerpt:
        excerpt = remove_emoji(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
