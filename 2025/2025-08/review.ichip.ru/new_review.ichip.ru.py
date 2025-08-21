from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://ichip.ru/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(., "Обзоры")]/ul/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name, cat_url=url))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if 'Топ-' not in title:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    if revs:
        next_page = context.get('page', 1) + 1
        next_url = context['cat_url'] + '?page={}'.format(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context, page=next_page))


def process_review(data, context, session):
    title = data.xpath('//h1/text()').string()

    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]
    product.category = context['cat']

    name = data.xpath('//h2[contains(., "Технические характеристики")]//text()').string(multiple=True)
    if name:
        product.name = name.replace('Технические характеристики', '').strip(' :')

    if not product.name:
        product.name = title.replace('Обзор геймерского внешнего диска ', '').replace('Предварительный обзор ', '').replace('Обзор смартфона ', '').replace('Обзор ноутбука ', '').replace('Обзор мини-ПК ', '').replace('Обзор корпуса ', '').replace('Обзор жесткого диска ', '').replace('Тест накопителя ', '').replace('Обзор накопителя ', '').replace('Обзор лазерного ', '').replace('Обзор монитора ', '').replace('Обзор внешнего накопителя ', '').replace('Обзор игровой гарнитуры ', '').replace('Обзор умного ', '').replace('Обзор камеры моментальной печати ', '').replace('Обзор наушников ', '').replace('Обзор тонкого пауэрбанка ', '').replace('Обзор умных часов ', '').replace('Обзор TWS-наушников ', '').replace('Обзор телевизора ', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//meta[@itemprop="datePublished"]/@content').string()

    author = data.xpath('//div[@class="article-author__name"]//text()').string(multiple=True)
    author_url = data.xpath('//div[@class="article-author__name"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "review-final-score")]/text()').string(multiple=True)
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    if not grade_overall:
        grade_overall = data.xpath('//div[contains(@class, "rating rating--")]/@class').string()
        if grade_overall:
            grade_overall = float(grade_overall.split('-')[-1]) / 2
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    grades = data.xpath('//div[@class="TestRating"]//ul[@class="ul-line"]/li')
    for grade in grades:
        grade_name, grade_val = grade.xpath('.//text()').string(multiple=True).split(':')
        grade_val = re.search(r'\d+\.?\d*', grade_val)

        if grade_val:
            grade_val = float(grade_val.group())
            review.grades.append(Grade(name=grade_name, value=grade_val, best=100.0))

    pros = data.xpath('//span[@class="plus"]//text()')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[@class="minus"]//text()')
    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@itemprop="description"]//text()').string(multiple=True)
    if summary and '[...]' not in summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "Итог", "i")]/following-sibling::p[not(regexp:test(., "Читайте также|Фото: компании-производители"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "review-summary-content")]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Итог", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "article-content")]/p[not(regexp:test(., "Читайте также|Фото: компании-производители"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body/p[not(@class or regexp:test(., "Читайте также|Фото: компании-производители"))]//text()').string(multiple=True)

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        if len(excerpt) > 3:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
