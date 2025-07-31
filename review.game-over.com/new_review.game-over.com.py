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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.game-over.com/content/category/reviews/', use='curl'), process_revlist, dict(cat='Tech'))
    session.queue(Request('https://www.game-over.com/review/gamereview.php', use='curl'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//td[@valign="top" and @align="center"]/a[.//b]')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl'), process_category, dict(cat=name))


def process_category(data, context, session):
    strip_namespace(data)

    months = data.xpath('//td[h3[contains(., "Review Archives")]]/a/@href')
    for month in months:
        url = month.string()
        session.queue(Request(url, use='curl'), process_revlist, dict(context))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h2/a|//tbody[tr/td[contains(., "Title")]]/tr/td/a')
    for rev in revs:
        title = rev.xpath('.//text()').string(multiple=True)
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace(' Review', '').replace(' Hands-On Preview', '').strip()
    product.url = context['url']
    product.category = context.get('cat').replace(' / ', '/')

    product.ssid = product.url.split('/')[-1].replace('.html', '')
    if not product.ssid:
        product.ssid = product.url.split('/')[-2]

    manufacturer = data.xpath('//strong[contains(text(), "Publisher:")]/text()|//td[img[@alt="Game & Publisher"]]/following-sibling::td//a//text()').string()
    if manufacturer:
        product.manufacturer = manufacturer.split(':')[-1].strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[@class="postauthor"]/p/text()[contains(., "on ")]|//td[img[@alt="Date Published"]]/following-sibling::td/font/text()').string()
    if date:
        review.date = date.split(', ', 1)[-1].split(' at ')[0].strip(' ·,.')

    author = data.xpath('//a[@rel="author"]/text()|//font[contains(text(), "By:")]/a//text()').string(multiple=True)
    author_url = data.xpath('(//a[@rel="author"]|//font[contains(text(), "By:")]/a)/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//strong[contains(text(), "Rating:")]/text()|//td[img[@alt="Overall Rating"]]/following-sibling::td/font/text()').string()
    if grade_overall:
        grade_overall = re.search(r'\d+[\.,]?\d?', grade_overall)
        if grade_overall:
            grade_overall = grade_overall.group()
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//b[regexp:test(text(), "\w+ \(\d+/\d+\)")]')
    for grade in grades:
        grade_name, grade_val = grade.xpath('text()').string().split()
        grade_val, grade_best = grade_val.strip('( :)').split('/')
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=float(grade_best)))

    pro = data.xpath('//strong[contains(text(), "The Good")]/following-sibling::text()[1]').string(multiple=True)
    if pro:
        pro = pro.strip(' +-*:;•,–')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    con = data.xpath('//strong[contains(text(), "The Bad")]/following-sibling::text()[1]').string(multiple=True)
    if con:
        con = con.strip(' +-*:;•,–')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    excerpt = data.xpath('//div[@class="article"]/p[not(@class or strong[regexp:test(text(), "The Good|The Bad|The Ugly|Reviewed By|Rating")] or contains(., "——————"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="KonaBody"]/p//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace('�', '').strip()
        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
