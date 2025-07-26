from agent import *
from models.products import *
import re


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
    session.queue(Request('https://www.binomania.it/recensioni-binomania/', use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[contains(@class, "entry-content")]/p[strong]|//div[contains(@class, "entry-content")]/strong')
    for cat in cats:
        cat_name = cat.xpath('.//text()').string()

        if cat_name:
            revs = cat.xpath('(following-sibling::ul)[1]/li/a')
            for rev in revs:
                title = rev.xpath('text()').string()
                url = rev.xpath('@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(cat=cat_name.strip(' :'), title=title, url=url))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('Video recensione dello ', '').replace('Video recensione del ', '').replace('Videorecensione del ', '').replace(' video e recensione', '').replace('Video e recensione del ', '').replace('Video e recensione dei ', '').replace('Recensione del ', '').replace('Recensione ', '').split(' – ')[0].replace('Preview dei ', '').replace(' videorecensione', '').split('- preview')[0].split(': recensione')[0].replace(' preview', '').replace('Test approfondito:', '').replace('Video recensione ', '').split('- preview')[0].replace(' video e recensione', '').replace(' preview', '').replace(' videorecensione', '').replace('RECENSIONE DEL ', '').replace('Video recensione ', '').replace('Preview ', '').split(': prestazioni')[0].replace('. la video recensione', '').replace('RECENSIONE DELLA ', '').replace('Videorecensione della ', '').strip().capitalize()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('recensione-', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//span[@class="cutemag-entry-meta-single-date"]/text()').string()

    author = data.xpath('//span[@itemprop="author"]//text()').string(multiple=True)
    author_url = data.xpath('//span[@itemprop="author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('(//p[strong[contains(., "Pregi:")]]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p[strong[contains(., "Difetti:")]]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('(//h2[regexp:test(., "CONCLUSIONE", "i")]/following-sibling::p|//h2[regexp:test(., "CONCLUSIONE", "i")]/following-sibling::blockquote)//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[regexp:test(., "In sintesi", "i")]/following-sibling::p[not(regexp:test(., "Pregi:|Difetti:"))]//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "CONCLUSIONE", "i")]/preceding-sibling::p[not(regexp:test(., "Pregi:|Difetti:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[regexp:test(., "In sintesi", "i")]/preceding-sibling::p[not(regexp:test(., "Pregi:|Difetti:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(regexp:test(., "Pregi:|Difetti:"))]//text()').string(multiple=True)

    if excerpt:
        excerpt = remove_emoji(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
