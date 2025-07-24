from agent import *
from models.products import *
import re


XCAT = ['English Articles']


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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.xtremehardware.com/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[a[contains(., "Recensioni")]]//ul[contains(@class, "level1")]/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('.//ul[contains(@class, "level2")]//a[not(contains(., "Recensioni"))]')
            if sub_cats:
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath('text()').string()
                    url = sub_cat.xpath('@href').string()
                    session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name + '|' + sub_name, cat_url=url))
            else:
                url = cat.xpath('a/@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name, cat_url=url))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url + '?showall=1', use='curl', force_charset='utf-8'), process_review, dict(context, url=url))

    page_cnt = data.xpath('//div[contains(text(), "Show more post")]/@data-pages').string()
    page = context.get('page', 1)
    if page_cnt and page < int(page_cnt):
        offset = context.get('offset', 0) + 13
        next_url = context['cat_url'] + '?limit=13&start={}&tmpl=component'.format(offset)
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context, page=page+1, offset=offset))


def process_review(data, context, session):
    strip_namespace(data)

    title = data.xpath('//h1[@class="article-title"]//text()').string(multiple=True)
    if not title:
        return

    product = Product()
    product.name = title.split(': ')[0].replace('', '').strip()
    product.ssid = context['url'].split('/')[-1].split('-')[0]
    product.category = context['cat']

    product.url = data.xpath('//a[contains(., "Vedi Offerta")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="author"]/@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//tr[contains(., "Complessivo")]//img/@alt').string()
    if grade_overall:
        grade_overall = grade_overall.split()[0].replace(',', '.')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//h1[contains(., "Conclusioni")]/following-sibling::table//tr[not(contains(., "Complessivo"))]')
    if not grades:
        grades = data.xpath('//p[.//strong[contains(., "Conclusioni")]]/following-sibling::table//tr[not(contains(., "Complessivo"))]')

    for grade in grades:
        grade_name = grade.xpath('.//strong/text()').string()
        grade_desc = grade.xpath('.//p[not(strong or img)]/text()').string(multiple=True) or grade.xpath('td/text()').string()
        grade_val = grade.xpath('.//img/@alt').string()
        if grade_val:
            grade_val = re.search(r'\d+[,\.]?\d?', grade_val).group().replace(',', '.')
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0, description=grade_desc))

    pros = data.xpath('(//p[strong[contains(text(), "Pro")]]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p[strong[contains(text(), "Contro")]]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//section[contains(@class, "article-content")]/p[@align="center"]//text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h1[contains(., "Conclusioni")]/following-sibling::p[not(strong[regexp:test(text(), "Pro|Contro")] or @align)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[.//strong[contains(., "Conclusioni")]]/following-sibling::p[not(strong[regexp:test(text(), "Pro|Contro")] or @align)]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    pages = data.xpath('//select[@class="form-control"]/option')
    for page in pages:
        title = page.xpath('text()').string()
        page_url = 'https://www.xtremehardware.com' + page.xpath('@value').string()
        review.add_property(type='pages', value=dict(title=title, url=page_url))

    excerpt = data.xpath('//h1[contains(., "Conclusioni")]/preceding-sibling::p[not(@align)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[.//strong[contains(., "Conclusioni")]]/preceding-sibling::p[not(@align)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//section[contains(@class, "article-content")]/p[not(strong[regexp:test(text(), "Pro|Contro")] or @align)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
