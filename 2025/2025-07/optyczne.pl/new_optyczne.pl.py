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
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('http://www.optyczne.pl/Testy_aparatów_Testy_obiektywów_Testy_lornetek_Inne_testy.html', use='curl'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class[regexp:test(., "tests-nav")]]/li/a')
    for cat in cats:
        name = cat.xpath('.//text()[string-length(normalize-space(.))>0]').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl'), process_category, dict(cat=name))


def process_category(data, context, session):
    url = 'https://www.optyczne.pl/index.html?'
    params = data.xpath('//div[@class="search-product"]/form/input|//div[@class="search-product"]/form//select')
    for param in params:
        name = param.xpath('@name').string()
        value = param.xpath('@value|(option)[1]/@value') or param.xpath('(option)[1]/text()')
        value = value.string()
        url += '&' + name + '=' + value

    if params:
        session.queue(Request(url + '&sort=&szukaj=Wyszukaj&szukaj=Wyszukaj', use='curl'), process_revlist, dict(context))
    else:
        process_revlist(data, context, session)


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//div[@class="product-content"]/h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl'), process_review, dict(context, title=title, url=url))

# no next page


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' - test')[0].replace('Test ', '').strip().capitalize()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.htm', '')

    product.category = context['cat'].replace('Inne testy', '').replace('Testy ', '').strip().capitalize()
    if not product.category:
        product.category = 'Technologia'

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//hq[@class="article-title"]/text()').string()
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//div[@class="calendar-date"]/text()').string()

    author = data.xpath('//span[contains(@class, "author-link")]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//tr[@class="test-result"]/td/span/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.replace('%', ''))
        review.grades.append(Grade(type='overall', value=grade_overall, best=100.0))

    pros = data.xpath('(//*[contains(text(), "Zalety")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = remove_emoji(pro).strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//*[contains(text(), "Wady")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = remove_emoji(con).strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclsuion = data.xpath('//h2[contains(text(), "Podsumowanie")]/following-sibling::text()|(//h2[contains(text(), "Podsumowanie")]/following-sibling::a|//h2[contains(text(), "Podsumowanie")]/following-sibling::p)//text()').string(multiple=True)
    if conclsuion:
        conclsuion = remove_emoji(conclsuion).strip()
        review.add_property(type='conclusion', value=conclsuion)

    excerpt = data.xpath('//h2[contains(text(), "Podsumowanie")]/preceding-sibling::text()|(//h2[contains(text(), "Podsumowanie")]/preceding-sibling::a|//h2[contains(text(), "Podsumowanie")]/preceding-sibling::p)//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="shortcode-content"]/text()|(//div[@class="shortcode-content"]/a|//div[@class="shortcode-content"]/p)[not(contains(., "Przykładowe zdjęcia"))]//text()').string(multiple=True)

    conclusion_url = ''
    pages = data.xpath('//ul[li[contains(., "Wstęp")]]/li/a')
    for page in pages:
        title = page.xpath('text()').string()
        page_url = page.xpath('@href').string()
        review.add_property(type='pages', value=dict(title=title, url=page_url))

        if 'podsumowanie' in title.lower():
            conclusion_url = page_url

    if pages and conclusion_url:
        session.do(Request(conclusion_url, use='curl'), process_conclusion, dict(excerpt=excerpt, review=review, product=product))

    elif excerpt:
        excerpt = remove_emoji(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_conclusion(data, context, session):
    strip_namespace(data)

    review = context['review']

    grade_overall = data.xpath('//tr[@class="test-result"]/td/span/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.replace('%', ''))
        review.grades.append(Grade(type='overall', value=grade_overall, best=100.0))

    pros = data.xpath('(//*[contains(text(), "Zalety")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = remove_emoji(pro).strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//*[contains(text(), "Wady")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = remove_emoji(con).strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclsuion = data.xpath('//div[@class="shortcode-content"]/text()|(//div[@class="shortcode-content"]/a|//div[@class="shortcode-content"]/p)[not(contains(., "Przykładowe zdjęcia"))]//text()').string(multiple=True)
    if conclsuion:
        conclsuion = remove_emoji(conclsuion).strip()
        review.add_property(type='conclusion', value=conclsuion)

    if context['excerpt']:
        context['excerpt'] = remove_emoji(context['excerpt']).strip()
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
