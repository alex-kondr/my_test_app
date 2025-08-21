from agent import *
from models.products import *


OPTIONS = """-H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: consentUUID=032b7d9d-7fdf-46c3-b614-14153a4501a0_47'"""


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


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.whatcar.com/reviews', use='curl', force_charset='utf-8', options=OPTIONS), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//a[@data-section="find-by-make"]')
    for cat in cats:
        manufacturer = cat.xpath('div[contains(@class, "displayName")]/text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS), process_revlist, dict(manufacturer=manufacturer))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//a[contains(@class, "CardVertical_linkContainer")]')
    for rev in revs:
        name = rev.xpath('.//h3[contains(@class, "classCardContentTitle")]/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS), process_review, dict(context, name=name, url=url))

#  no next page


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.ssid = context['url'].split('/')[-1]
    product.category = data.xpath('//p[contains(@class, "categoryRow")]/a/text()').string()
    product.manufacturer = context['manufacturer']

    product.url = data.xpath('//a[contains(., "New car deals") and @product-id]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[contains(@class, "title")]//text()').string(multiple=True)
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//span[contains(@class, "Date_date--published")]/text()').string()

    author = data.xpath('//div[contains(@class, "authorCardName")]/text()').string()
    author_url = data.xpath('//div[contains(@class, "AuthorDate_container")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count((//div[div[@id="introduction"]]/div[contains(@class, "Rating_rating")])[1]/div[contains(@class, "Icon_red")])')
    if grade_overall:
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    grades = data.xpath('//div[@class="Grid_row___ZDUK"]/div/h3[contains(@class, "subChapterTitle")]')
    if not grades:
        grades = data.xpath('//div[@class="Grid_row___ZDUK"]/div/h2[contains(@class, "chapterMainTitle")]')

    for grade in grades:
        grade_name = grade.xpath('text()').string()
        grade_val = grade.xpath('count((following-sibling::div)[1][contains(@class, "Rating_rating")]/div[contains(@class, "Icon_red")])')
        if grade_name and grade_val > 0:
            review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    pros = data.xpath('//ul[contains(@class, "classVerdictBoxPros")]/li|//div[h4[contains(., "Strengths")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[contains(@class, "classVerdictBoxCons")]/li|//div[h4[contains(., "Weaknesses")]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "promoBoxText")]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[div/h2[contains(text(), "Overview")]]/h4[contains(@class, "VerdictBox")]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "classBodyText")]/p[@dir="ltr"]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
