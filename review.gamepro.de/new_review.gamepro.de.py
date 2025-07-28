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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.gamepro.de/tests/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = data.xpath('//div[@class="media-body"]/p/a/text()').string() or context['title'].split(' im Test')[0].replace('', '').strip()
    product.url = context['url']
    product.ssid = product.url.split(',')[-1].replace('.html', '')
    product.category = 'Spiele'

    platform = data.xpath('//p[@class="info" and contains(., "Release:")]/text()').string()
    if platform:
        platform = re.search(r'\(.+\)', platform)
        if platform:
            product.category += '|' + platform.group().strip('( )').replace(',', '/')

    genre = data.xpath('//p[@class="info" and contains(., "Genre:")]/text()').string()
    if genre:
        product.category += '|' + genre.replace('Genre:', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//p[contains(@class, "publication-info")]/*/text()').string()
    author_url = data.xpath('//p[contains(@class, "publication-info")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2].split(',')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="points responsive"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//div[contains(@class, "wertungskasten-box-item") and .//i]')
    for grade in grades:
        grade_name = grade.xpath('div[@class="wertungskasten-title"]/text()').string()
        grade_val = grade.xpath('count(div[contains(@class, "star-rating")]/i[contains(@class, "active")])')
        if grade_name and grade_val:
            review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    pros = data.xpath('//div[@class="pro"]//li/span')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="contra"]//li/span')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="intro"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Fazit")]/following-sibling::p[not(@class)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Fazit")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="article-content"]/p[not(@class)]//text()').string(multiple=True)

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        title = review.title + ' - Pagina 1'
        review.add_property(type='pages', value=dict(title=title, url=data.response_url))
        session.do(Request(next_url, use='curl', force_charset='utf-8'), process_review_next, dict(excerpt=excerpt, review=review, product=product))

    elif excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_next(data, context, session):
    strip_namespace(data)

    review = context['review']

    page =context.get('page', 2)
    title = review.title + ' - Pagina ' + str(page)
    review.add_property(type='pages', value=dict(title=title, url=data.response_url))

    grade_overall = data.xpath('//span[@class="points responsive"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//div[contains(@class, "wertungskasten-box-item") and .//i]')
    for grade in grades:
        grade_name = grade.xpath('div[@class="wertungskasten-title"]/text()').string()
        grade_val = grade.xpath('count(div[contains(@class, "star-rating")]/i[contains(@class, "active")])')
        if grade_name and grade_val:
            review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    pros = data.xpath('//div[@class="pro"]//li/span')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="contra"]//li/span')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "Fazit")]/following-sibling::p[not(@class)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Fazit")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="article-content"]/p[not(@class)]//text()').string(multiple=True)

    if excerpt:
        context['excerpt'] += ' ' + excerpt

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.do(Request(next_url, use='curl', force_charset='utf-8'), process_review_next, dict(context, review=review, page=page+1))

    elif context['excerpt']:
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
