from agent import *
from models.products import *
import re


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflated' -H 'Connection: keep-alive' -H 'Cookie: TCF_COOKIE=CQaxgwAQaxgwAFDADBDECEFsAP_gAEPgAAYgLlNR_G__bWlr-bb3aftkeYxP9_hr7sQxBgbJk24FzLvW7JwWx2E5NAzatqIKmRIAu3TBIQNlHJDURVCgKIgVryDMaEyUoTNKJ6BkiFMRI2NYCFxvm4tjWQCY5vr99lc1mB-N7dr82dzyy6hHn3a5_2S1WJCdIYetDfv8ZBKT-9IEd_x8v4v4_F7pE2-eS1n_pGvp6j9-YnM_dBmxt-bSffzPn__rl_e7X_vd_n37v94XH77v____f_-7_wXIaj-N_62vLf8WCvw_bIcxi_7_AH3YhiCA2TRswLmXUtyRgtvsJmSJE0YUwQMiABRuiCQAJSMDCIiKFCERAqXiGYAJghQmaQQ8DJAGYixMCgAJCfFxbGsgEzydT86K77ElsZybXtsrlkk3BHfuVa8skqoTE4UwYKO9bYwCAj1eQp7uiVrRaR-Z3SJgUgBjf_KNTL0uw9xOOerTXia8zk6Yl--5Lnv-92idMz977Z9f2k7_2fzeutzd_-2AAAAA.YAAAAAAAAAAA; borlabs-cookie=%7B%22consents%22%3A%7B%22essential%22%3A%5B%22borlabs-cookie%22%5D%7D%2C%22domainPath%22%3A%22www.hartware.de%2F%22%2C%22expires%22%3A%22Sun%2C%2011%20Jan%202026%2008%3A07%3A14%20GMT%22%2C%22uid%22%3A%22wzlxoy59-rj2wkzg9-8d2klvs7-xapfslgp%22%2C%22v3%22%3Atrue%2C%22version%22%3A1%7D' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""


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
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.hartware.de/category/reviews/', use='curl', force_charset='utf-8', max_age=0, options=OPTIONS), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if ' Preview' not in title:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0, options=OPTIONS), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0, options=OPTIONS), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' im ')[0].replace('Test: ', '').replace(' Kurztest', '').replace(' Test Bench', '').replace('Kurztest: ', '').replace('Praxistest: ', '').replace('User-Review: ', '').replace('Kurztest ', '').replace(' Extremtest', '').replace('Nachtest des ', '').replace(' Nachtest', '').replace(' angetestet', '').replace(' Review', '').split(' – ')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].split('-im-')[0]

    product.category = data.xpath('(//a[@rel="category tag"])[1][not(regexp:test(., "Reviews|Sonstiges"))]/text()').string()
    if not product.category:
        product.category = 'Technik'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[@class="date"]/text()').string(multiple=True)
    if date:
        review.date = date.split(', ')[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//h2//text()').string(multiple=True)
    if summary:
        summary = remove_emoji(summary)
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@class="entry-inner"]/p//text()').string(multiple=True)

    pages = data.xpath('(//ul[@id="toc_review"])[1]//a')
    for page in pages:
        title = page.xpath('.//text()').string(multiple=True)
        page_url = page.xpath('@href').string()
        review.add_property(type='pages', value=dict(title=title, url=page_url))

    if pages:
        session.do(Request(page_url, use='curl', force_charset='utf-8', max_age=0, options=OPTIONS), process_review_last, dict(excerpt=excerpt, review=review, product=product))

    elif excerpt:
        excerpt = remove_emoji(excerpt)
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_last(data, context, session):
    strip_namespace(data)

    review = context['review']

    pros = data.xpath('//p[strong[contains(., "Positiv:")]]/text()')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[strong[contains(., "Negativ:")]]/text()')
    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "Fazit")]/following-sibling::p[not(regexp:test(., "Positiv|Negativ|Neutral"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="entry-inner"]/p[not(regexp:test(., "Positiv|Negativ|Neutral"))]//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion)
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Fazit")]/preceding-sibling::p//text()').string(multiple=True)
    if excerpt:
        context['excerpt'] += ' ' + excerpt

    if context['excerpt']:
        context['excerpt'] = remove_emoji(context['excerpt'])
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)

