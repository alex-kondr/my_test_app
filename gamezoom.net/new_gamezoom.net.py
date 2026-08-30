from agent import *
from models.products import *
import simplejson


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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    options = """--globoff --compressed -H 'Authorization: Bearer 7f0khGnFfomuYqcF2cO-in5uz1CXgDhq'"""
    url = 'https://admin.gamezoom.net/items/article?sort[]=-date_activation&meta=filter_count&limit=21&offset=0&filter[_and][1][status][_eq]=published&filter[_and][2][isArticle][_eq]=true&filter[_and][3][_or][0][featured][_null]=true&filter[_and][3][_or][1][featured][_nin]=both,gamezoom&filter[_and][4][_or][0][type][_eq]=1&filter[_and][4][_or][1][type][_null]=true&fields=title,id'
    session.queue(Request(url, use='curl', force_charset='utf-8', options=options, max_age=0), process_revlist, dict(cat_url=url))
    url = 'https://admin.gamezoom.net/items/article?sort[]=-date_activation&meta=filter_count&limit=21&offset=0&filter[_and][1][status][_eq]=published&filter[_and][2][isArticle][_eq]=true&filter[_and][3][_or][0][featured][_null]=true&filter[_and][3][_or][1][featured][_nin]=both,gamezoom&filter[_and][4][_or][0][type][_eq]=2&filter[_and][4][_or][1][type][_null]=true&fields=title,id'
    session.queue(Request(url, use='curl', force_charset='utf-8', options=options, max_age=0), process_revlist, dict(cat_url=url))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('data', [])
    for rev in revs:
        title = rev.get('title')
        ssid = str(rev.get('id'))
        url = 'https://www.gamezoom.net/artikel/' + ssid
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, ssid=ssid, url=url))

    revs_cnt = context.get('revs_cnt', revs_json.get('meta', {}).get('filter_count', 0))
    offset = context.get('offset', 0) + 21
    if offset < revs_cnt:
        next_url = context['cat_url'].replace('offset=0', 'offset='+str(offset))
        options = """--globoff --compressed -H 'Authorization: Bearer 7f0khGnFfomuYqcF2cO-in5uz1CXgDhq'"""
        session.queue(Request(next_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_revlist, dict(context, offset=offset, revs_cnt=revs_cnt))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace(' - Test/Review', '').strip()
    product.ssid = context['ssid']
    product.manufacturer = data.xpath('//div[contains(div/p, "Entwickler")]/div[contains(@class, "right")]/p/text()').string()

    product.url = data.xpath('//div[contains(div/p, "Webseite")]/div[contains(@class, "right")]/a/@href').string()
    if not product.url:
        product.url = context['url']

    category = data.xpath('//a[contains(@class, "category")]/span/text()').string()
    platforms = data.xpath('//div[contains(div/p, "Plattform")]/div[contains(@class, "right")]/p/text()').join('/')
    if category and platforms:
        product.category = 'Spiele' + '|' + category + '|' + platforms
    elif category:
        product.category = category
    else:
        product.category = 'Technik'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[contains(@class, "article_author_date")]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "article_author_date")]/b/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "evaluation__chart-center")]/span/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//div[contains(@class, "bar badge")]')
    for grade in grades:
        grade_name = grade.xpath('span[contains(@class, "title")]/text()').string()
        grade_val = grade.xpath('.//span[contains(@class, "valuation_number__text")]/text()').string()
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
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[contains(@class, "evaluation__text")]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//section[contains(@class, "content")]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
