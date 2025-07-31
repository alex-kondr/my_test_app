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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://dailynintendo.nl/category/reviews/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = re.sub(r'\([^\(\)]+\)', '', context['title']).split(' – ')[0].replace('[Review]', '').replace('[REVIEW]', '').replace('[REVIEW ]', '').replace('[Preview]', '').replace('[PREVIEW]', '').replace('[SWITCH REVIEW]', '').replace('[N3DS REVIEW]', '').replace('[Gamescom] Preview:', '').replace('[Gamescom] Preview', '').replace('[Gamescom] ', '').replace(' Preview', '').replace('3DS Review: ', '').replace('3DS eShop Review:', '').replace('Wii Review: ', '').replace('3DS Video Review: ', '').replace('DS Review: ', '').replace('Wii/3DS review: ', '').replace('Wii U eShop Review: ', '').replace('Wii U eshop review: ', '').replace('Wii U Review: ', '').replace('New 3DS review: ', '').replace('Review: ', '').replace('[Mini-Review]', '').replace('Wii U review:', '').replace('“Review”:', '').replace(' review online!', '').replace('[3DS XL review]', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('review-', '')
    product.category = 'Techniek'

    platform = re.search(r'\([^\(\)]+\)', context['title'])
    if platform:
        product.category = 'Spellen|' + platform.group().strip('( )')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "post-author-name")]/a/text()').string()
    author_url = data.xpath('//div[contains(@class, "post-author-name")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "review-final-score")]/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('(//strong|//p)[regexp:test(., "Eindcijfer.+\d+|Totaal.+\d+")]/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('//li[regexp:test(., "Eindcijfer.+\d+|Totaal.+\d+")]/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('(//h2|//p)[regexp:test(., "DN-Score:", "i")]//text()').string()

    if grade_overall:
        try:
            grade_overall = float(grade_overall.split(':')[-1].strip().rsplit()[-1].replace(',', '.'))
            if 10 < grade_overall < 101:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))
            elif grade_overall < 11:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))
        except:
            pass

    grades = data.xpath('//li[@class="blocks-gallery-item"]//img/@alt')
    if not grades:
        grades = data.xpath('(//strong|//p)[regexp:test(., "\w+: \d{1,2}[\.,]?/10?") and not(regexp:test(., "Totaal|Eindcijfer|DN-scoer", "i"))]/text()')
    if not grades:
        grades = data.xpath('//li[regexp:test(., "\w+ \d{1,2}[\.,]?/10") and not(regexp:test(., "Totaal|Eindcijfer|DN-score", "i"))]/text()')
    if not grades:
        grades = data.xpath('//strong[regexp:test(., ".+\d{1,2}[\.,]?(/10)?") and not(regexp:test(., "Totaal|Eindcijfer|DN-score", "i"))]/text()')

    for grade in grades:
        grade = grade.string().replace('Review ', '').strip()
        try:
            if ':' in grade:
                grade_name, grade_val = grade.split(':')
            else:
                grade_name, grade_val = grade.split(' ', 1)

            grade_val = float(grade_val.replace(',', '.').split('/')[0])
            if grade_val < 11:
                review.grades.append(Grade(name=grade_name, value=grade_val, best=10.0))
        except:
            pass

    pros = data.xpath('//p[contains(@class, "has-vivid-green")]//text()')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[@style="color:#f93f3f"]//text()')
    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('((//h2|//p)[regexp:test(., "conclusie", "i")])[last()]/following-sibling::p[not(regexp:test(., "Graphics|Gameplay|Eindcijfer|Beoordeling|Geluid|Speelduur|Totaal") or @class)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "review-summary-content")]//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2|//p)[regexp:test(., "conclusie", "i")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "post-content")]/p[not(regexp:test(., "Graphics|Gameplay|Eindcijfer|Beoordeling|Geluid|Speelduur|Totaal") or @class)]//text()').string(multiple=True)

    if excerpt:
        excerpt = remove_emoji(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
