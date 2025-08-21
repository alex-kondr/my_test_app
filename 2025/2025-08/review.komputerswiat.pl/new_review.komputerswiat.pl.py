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
    session.queue(Request('https://www.komputerswiat.pl/recenzje/sprzet', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//a[contains(@class, "card__link")]')
    for rev in revs:
        title = rev.xpath('.//h3[contains(@class, "card__title")]/text()').string()
        cat = rev.xpath('.//span[contains(@class, "card__category") and not(regexp:test(., "Inne"))]/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, cat=cat, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('Test ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat'] or 'Technologia'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "author__name")]/text()').string()
    author_url = data.xpath('//a[contains(@class, "author--link")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//tr[contains(., "Ocena końcowa")]/th[not(contains(., "Ocena końcowa"))]/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.split()[0].replace(',', '.'))
        review.grades.append(Grade(type='overall', value=grade_overall, best=100.0))

    grades = data.xpath('//tbody[contains(., "Ocena końcowa")]/tr[not(contains(., "Ocena końcowa")) and td]')
    for grade in grades:
        grade_name = grade.xpath('td[not(contains(., " punkt"))]/text()').string()
        grade_val = grade.xpath('td[contains(., " punkt")]/text()').string().split()[0].replace(',', '.')
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100.0))

    summary = data.xpath('//p[@class="ods-a-lead-text"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Podsumowanie")]/following-sibling::p[not(regexp:test(., "aktualne ceny") or u or preceding-sibling::p/u)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Czy warto kupić")]/following-sibling::p[not(regexp:test(., "aktualne ceny") or u or preceding-sibling::p/u)]//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    if data.xpath('//div[@class="contentPremium"]/p'):
        excerpt = data.xpath('(//article[@data-section="article-body"]/p|//h2[contains(., "Podsumowanie")]/preceding-sibling::p)[not(regexp:test(., "linki reklamowe|aktualne ceny") or u or preceding-sibling::p/u)]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('(//article[@data-section="article-body"]/p|//h2[contains(., "Czy warto kupić")]/preceding-sibling::p)[not(regexp:test(., "linki reklamowe|aktualne ceny") or u or preceding-sibling::p/u)]//text()').string(multiple=True)
    else:
        excerpt = data.xpath('//h2[contains(., "Podsumowanie")]/preceding-sibling::p[not(regexp:test(., "linki reklamowe|aktualne ceny") or u or preceding-sibling::p/u)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Czy warto kupić")]/preceding-sibling::p[not(regexp:test(., "linki reklamowe|aktualne ceny") or u or preceding-sibling::p/u)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//article[@data-section="article-body"]|//div[@class="contentPremium"])/p[not(regexp:test(., "linki reklamowe|aktualne ceny") or u or preceding-sibling::p/u)]//text()').string(multiple=True)

    if excerpt:
        excerpt = remove_emoji(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
