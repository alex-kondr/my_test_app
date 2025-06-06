from agent import *
from models.products import *


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
    session.queue(Request('https://www.tech-review.de/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[a[contains(., "Tests")]]/ul//a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h4[a]')
    for rev in revs:
        name = rev.xpath('a[last()]/text()').string()
        url = rev.xpath('a[last()]/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name'].split(': ')[0].replace(' im Test!', '').replace('be quiet! ', '').replace(' im TRV-Test', '').replace(' im Chroma-Test', '').replace(' im RoundUp-Test', '').replace(' im Test', '').strip()
    product.category = context['cat']

    ssid = context['url'].split('/')[-1]
    if not ssid:
        ssid = context['url'].split('/')[-2]

    product.ssid = ssid.replace('test-', '').replace('.html', '').replace('-im-test', '')

    product.url = data.xpath('//a[contains(., "Direkt zur Produktseite")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//section[@id="content"]/article/h3//text()').string(multiple=True)
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split()[0]

    author = data.xpath('//p[@class="author"]/text()').string()
    author_url = data.xpath('//img[contains(@src, "assets/avatars/team/")]/@src').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].replace('.jpg', '')
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grades = data.xpath('//ul[@class="awardsOld"]/li//@src')
    for grade in grades:
        grade = grade.string()
        grade_name = grade.split('Award_')[-1].split('_')[0].replace('.jpg', '')
        if 'Sehr_Gut' in grade:
            review.grades.append(Grade(type='overall', name=grade_name, value=3.0, best=3.0))
        elif '_Gut' in grade:
            review.grades.append(Grade(type='overall', name=grade_name, value=2.0, best=3.0))
        elif '_Befriedigend' in grade:
            review.grades.append(Grade(type='overall', name=grade_name, value=1.0, best=3.0))
        else:
            review.grades.append(Grade(type='overall', name=grade_name, value=0.0, best=3.0))

    pros = data.xpath('//ul/li[@class="positive"]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul/li[@class="negative"]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//section[@class="summaryText"]//p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@id, "page")]//p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
