from agent import *
from models.products import *
import time
import random
import re


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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://gsmonline.pl/testy', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    revs = data.xpath('//a[contains(@id, "article_big")]')
    for rev in revs:
        ssid = rev.xpath('@id').string().split('_')[-1]
        title = rev.xpath('.//h3/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, ssid=ssid, url=url))

    next_url = data.xpath('//a[@class="last"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = context['title'].replace('Test - ', '').split(' - ')[0].split(' – ')[0].split(': test')[0].replace('Rozpoczynamy testy ', '').replace('Zaczynamy testy ', '').replace('Nasz test ', '').replace('Testujemy ', '').replace('Przetestowaliśmy ', '').replace('Recenzja ', '').replace('Test ', '').strip().capitalize()
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = 'Technologia'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//div[@class="article-date"]/text()').string()

    author = data.xpath('//a[@class="author_email"]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//h3[normalize-space(.)="Zalety"]/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('(//p[strong[contains(., "Zalety:")]]/following-sibling::*)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = remove_emoji(pro).strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('(//p[strong[normalize-space(.)="Zalety:"]]/following-sibling::*)[1]/text()[normalize-space(.)]')
        for pro in pros:
            pro = pro.string(multiple=True)
            if pro:
                pro = remove_emoji(pro).strip(' +-*.:;•,–')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

    cons = data.xpath('//h3[normalize-space(.)="Wady"]/following-sibling::ul[1]/li')
    if not cons:
        cons = data.xpath('(//p[strong[contains(., "Wady:")]]/following-sibling::*)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = remove_emoji(con).strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('(//p[strong[normalize-space(.)="Wady:"]]/following-sibling::*)[1]/text()[normalize-space(.)]')
        for con in cons:
            con = con.string(multiple=True)
            if con:
                con = remove_emoji(con).strip(' +-*.:;•,–')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h3[contains(., "Podsumowanie")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[contains(., "Dla kogo ")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[b[contains(., "Podsumowanie")]]/following-sibling::p//text()|//b[contains(., "Podsumowanie")]/following-sibling::text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion).replace(u'', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h3[contains(., "Podsumowanie")])[1]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//h3[contains(., "Dla kogo ")])[1]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//b[contains(., "Podsumowanie")])[1]/preceding::p//text()|(//b[contains(., "Podsumowanie")])[1]/preceding-sibling::text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="article-full"]/p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="article-full"]//p[@align="justify" and not(preceding::b[contains(., "Dane techniczne:")])]//text()[not(contains(., "Dane techniczne:"))]').string(multiple=True)

    if excerpt:
        excerpt = remove_emoji(excerpt).replace(u'', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
