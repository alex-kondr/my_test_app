from agent import *
from models.products import *
import re


XCAT = ['Аналитика']


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
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request('https://top-mob.com/?s=%D0%9E%D0%91%D0%97%D0%9E%D0%A0', force_charset='utf-8'), process_revlist, {})


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//article[contains(@class, "post-")]')
    for rev in revs:
        title = rev.xpath(".//h2[@class='entry-title']//text()").string()
        ssid = rev.xpath('@id').string()
        grade_overall = rev.xpath('.//p[contains(., "Оценка:")]/b/text()').string()
        url = rev.xpath(".//h2[@class='entry-title']/a/@href").string()

        if title and 'O нас' not in title and url:
            session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=remove_emoji(title), ssid=ssid, grade_overall=grade_overall, url=url))

    page_cnt = context.get('page_cnt', data.xpath('//a[@class="page-numbers"][last()]/text()').string())
    next_page = context.get('page', 1) + 1
    if next_page <= int(page_cnt):
        next_url = 'https://top-mob.com/page/{}/?s=%D0%9E%D0%91%D0%97%D0%9E%D0%A0'.format(next_page)
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict(page_cnt=page_cnt, page=next_page))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' ОБЗОР: ')[0].split(' Обзор, ')[0].replace('Объективный обзор: ', '').split(': обзор ')[-1].replace(' ОБЗОР', '').replace('Обзор ', '').replace(' на обзоре', '').strip()
    product.ssid = context['ssid'].replace('post-', '')
    product.url = context['url']

    category = data.xpath("//span[@class='cat-links']/a//text()").string()
    if category:
        product.category = category.replace('Новости', '').replace('Как фотографировать', 'Технологии').strip()
    else:
        product.category = 'Технологии'

    if category in XCAT:
        return

    review = Review()
    review.title = context['title']
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']

    date = data.xpath("//time[@class='entry-date published']/@datetime").string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("//span[@class='author vcard']//text()").string(multiple=True)
    author_url = data.xpath("//span[@class='author vcard']/a/@href").string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    if context['grade_overall']:
        grade_overall = context['grade_overall'].split(' из ')[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('(//h2[contains(., "Преимущества")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h2[contains(., "Недостатки")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[regexp:test(., "Стоит ли покупать|Итог|Вывод|Рекомендац", "i")]/following-sibling::p[not(@class or small or regexp:test(., "Не забудьте заглянуть"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[contains(text(), "Выводы")]]/following-sibling::p//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Стоит ли покупать|Итог|Вывод|Рекомендац", "i")]/preceding-sibling::p[not(@class or @style or small or regexp:test(., "Не забудьте заглянуть"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[strong[contains(text(), "Выводы")]]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]//p[not(@class or @style or small or regexp:test(., "Не забудьте заглянуть"))]//text()').string(multiple=True)

    if excerpt:
        excerpt = remove_emoji(excerpt).replace('a href=»https://top-mob.com/vivo-x200-pro-mini-obzor-bolshoy-akkumuljator-sovremennyy-dizayn-chyotkoe-izobrazhenie/»>', '').replace('a href=»https://top-mob.com/samsung-galaxy-z-fold6-obzor-sgibaemyy-ekran-tonkiy-korpus-obyomnyy-nakopitel-besprovodnaja-zarjadka/»>', '').replace('< a href=»https://top-mob.com/honor-200-pro-obzor-obyomnyj-nakopitel-skorostnaja-zarjadka-chyotkoe-izobrazhenie/»>', '').replace('<a href=»', '').replace('</a>', '').strip()
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
