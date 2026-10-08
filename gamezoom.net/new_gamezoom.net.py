from agent import *
from models.products import *
import simplejson
import re
import time
import random


XTITLE = ['Preview-Video', 'Vorschau/Preview', 'Preview-Event', 'Preview Event', 'im Videotest', 'Preview Video', 'Preview/Vorschau', ' - Preview', 'Testvideo']


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
    session.sessionbreakers = [SessionBreak(max_requests=9000)]
    url = 'https://www.gamezoom.net/api/directus?url=https%3A%2F%2Fadmin.gamezoom.net%2Fitems%2Farticle%3Fsort%5B%5D%3D-date_activation%26meta%3Dfilter_count%26limit%3D21%26offset%3D0%26filter%5B_and%5D%5B0%5D%5Bdate_activation%5D%5B_lt%5D%3D2026-10-07T05%3A45%3A49.600Z%26filter%5B_and%5D%5B1%5D%5Bstatus%5D%5B_eq%5D%3Dpublished%26filter%5B_and%5D%5B2%5D%5BisArticle%5D%5B_eq%5D%3Dtrue%26filter%5B_and%5D%5B3%5D%5B_or%5D%5B0%5D%5Bfeatured%5D%5B_null%5D%3Dtrue%26filter%5B_and%5D%5B3%5D%5B_or%5D%5B1%5D%5Bfeatured%5D%5B_nin%5D%3Dboth%2Cgamezoom%26filter%5B_and%5D%5B4%5D%5B_or%5D%5B0%5D%5Btype%5D%5B_eq%5D%3D1%26filter%5B_and%5D%5B4%5D%5B_or%5D%5B1%5D%5Btype%5D%5B_null%5D%3Dtrue%26fields%3Dinternalname%2Ctype%2Ctitle%2Cteaser%2Cdate_activation%2Cid%2Cfeatured%2Cimage.id%2Cimage.filename_disk%2Cimage.metadata%2Cimage.width%2Cpicture.file.id%2Cpicture.file.filename_disk%2Cpicture.file.metadata%2Cpicture.file.width%2Cpicture.httppath%2Cproduct.hardware_category.*%2C%20product.game_category.*'
    session.queue(Request(url, force_charset='utf-8', max_age=0), process_revlist, dict(cat_url=url))
    url = 'https://www.gamezoom.net/api/directus?url=https%3A%2F%2Fadmin.gamezoom.net%2Fitems%2Farticle%3Fsort%5B%5D%3D-date_activation%26meta%3Dfilter_count%26limit%3D21%26offset%3D0%26filter%5B_and%5D%5B0%5D%5Bdate_activation%5D%5B_lt%5D%3D2026-10-07T05%3A46%3A41.393Z%26filter%5B_and%5D%5B1%5D%5Bstatus%5D%5B_eq%5D%3Dpublished%26filter%5B_and%5D%5B2%5D%5BisArticle%5D%5B_eq%5D%3Dtrue%26filter%5B_and%5D%5B3%5D%5B_or%5D%5B0%5D%5Bfeatured%5D%5B_null%5D%3Dtrue%26filter%5B_and%5D%5B3%5D%5B_or%5D%5B1%5D%5Bfeatured%5D%5B_nin%5D%3Dboth%2Cgamezoom%26filter%5B_and%5D%5B4%5D%5B_or%5D%5B0%5D%5Btype%5D%5B_eq%5D%3D2%26filter%5B_and%5D%5B4%5D%5B_or%5D%5B1%5D%5Btype%5D%5B_null%5D%3Dtrue%26fields%3Dinternalname%2Ctype%2Ctitle%2Cteaser%2Cdate_activation%2Cid%2Cfeatured%2Cimage.id%2Cimage.filename_disk%2Cimage.metadata%2Cimage.width%2Cpicture.file.id%2Cpicture.file.filename_disk%2Cpicture.file.metadata%2Cpicture.file.width%2Cpicture.httppath%2Cproduct.hardware_category.*%2C%20product.game_category.*'
    session.queue(Request(url, force_charset='utf-8', max_age=0), process_revlist, dict(cat_url=url))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(3, 10))

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('data', [])
    for rev in revs:
        title = rev.get('title')
        ssid = str(rev.get('id'))
        url = 'https://www.gamezoom.net/artikel/' + ssid

        if not any(xtitle in title for xtitle in XTITLE):
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, ssid=ssid, url=url))

    revs_cnt = context.get('revs_cnt', revs_json.get('meta', {}).get('filter_count', 0))
    offset = context.get('offset', 0) + 21
    if offset < revs_cnt:
        next_url = context['cat_url'].replace('offset%3D0', 'offset%3D'+str(offset))
        session.queue(Request(next_url, force_charset='utf-8', max_age=0), process_revlist, dict(context, offset=offset, revs_cnt=revs_cnt))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(3, 10))

    product = Product()
    product.name = context['title'].replace(' – Test/Review (+Video)', '').replace(' - Test/Review', '').replace(' -Test/Review', '').replace('- Test/Review', '').replace(' - Review/Test', '').replace(' – Mousepad-Review', '').replace(' - Test /Review', '').replace(' - (Kurz)Review', '').replace(' - Video-Review', '').replace(' Preview-Video', '').replace(' - Im Video-Test', '').replace(' – Test/Review', '').replace(' im Video-Test', '').replace('- Test/Review', '').replace(' im Test', '').replace(' - Test', '').replace(' - Review', '').replace(' – Review', '').replace(' (Video)', '').replace(' (+Xbox One Review)', '').replace(' (+Testvideo)', '').replace(' (+Testvideos)', '').replace(' (+Test-Video)', '').replace(' (inkl. Testvideo)', '').replace(' inkl. Testvideo', '').replace(' (+Video)', '').replace('- Review', '').replace('-Review', '').replace(' im Video-Test', '').replace(' Review' ,'').strip()
    product.ssid = context['ssid']
    product.manufacturer = data.xpath('//div[contains(div/p, "Entwickler")]/div[contains(@class, "right")]/p/text()').string()

    product.url = data.xpath('//div[contains(div/p, "Webseite")]/div[contains(@class, "right")]/a/@href').string()
    if not product.url:
        product.url = context['url']

    category = data.xpath('//a[contains(@class, "category")]/span/text()').string()
    platforms = data.xpath('//div[contains(div/p, "Plattform")]/div[contains(@class, "right")]/p/text()').strings()
    if category and platforms:
        product.category = 'Spiele' + '|' + '/'.join(set(platforms)) + '|' + category
    elif category:
        product.category = category
    else:
        product.category = 'Technik'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//div[contains(@class, "author_date")]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "author_date")]/b/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "evaluation__chart-center")]/span/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall)
        if grade_overall > 100:
            grade_overall = grade_overall / 10

        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//div[contains(@class, "bar badge")]')
    for grade in grades:
        grade_name = grade.xpath('span[contains(@class, "title")]/text()').string()
        grade_val = grade.xpath('.//span[contains(@class, "number__text")]/text()').string()
        if grade_name and grade_val and grade_val[0].isdigit() and float(grade_val) > 0:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100.0))

    pros = data.xpath('//div[contains(div, "Richtig gut")]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(div, "Verbesserungswürdig")]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "conclusion_short")]/p//text()').string(multiple=True)
    if summary:
        summary = summary.split(' meint: ')[-1]
        summary = re.sub(r'<[^>]+>', '', summary)
        summary = re.sub(r'&#\d+;', '', summary).strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[contains(@class, "conclusion_box")]/p[contains(@class, "evaluation__text")]//text()').string(multiple=True)
    if conclusion:
        conclusion = re.sub(r'<[^>]+>', '', conclusion)
        conclusion = re.sub(r'&#\d+;', '', conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//section[contains(@class, "content")]/p//text()').string(multiple=True)
    if excerpt:
        excerpt = re.sub(r'<[^>]+>', '', excerpt)
        excerpt = re.sub(r'&#\d+;', '', excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
