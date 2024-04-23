from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.dgl.ru/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="box-col"]')
    for rev in revs:
        url = rev.xpath('.//a[@class="box"]/@href').string()
        session.queue(Request(url), process_review, dict(url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.ssid = context['url'].split('/')[-1].replace('obzor-', '').replace('.html', '')
    product.category = "Технологии"

    product.url = data.xpath('//a[contains(., "здесь")]/@href').string()
    if not product.url:
        product.url = context['url']

    title = data.xpath('//meta[@name="title"]/@content').string()
    product.name = title.replace('Предварительный обзор:', '').replace('Предварительный обзор', '').replace('Обзор смартфона', '').replace('Stuff-обзор:', '').replace('Взгляд от Stuff:', '').replace('WHF-обзор:', '').replace('Взгляд журнала Stuff:', '').replace('Обзор наушников', '').replace('Мини-обзор:', '').replace('Блиц-обзор', '').replace('Обзор:', '').split(':')[0].split(' - ')[0].split(' — ')[0].strip()

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="article-author-name"]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count((//div[@class="rating"])[1]/div[@class="star full"])')
    if not grade_overall:
        grade_overall = data.xpath('count(//p[contains(., "Оценка в звездах")][1]//i[@class="td-icon-star"])')
    if grade_overall:
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    grades = data.xpath('//div[@class="article-part"]//tr[td[@colspan="1"] and not(@style)]')
    for grade in grades:
        grade_name = grade.xpath('td/strong/text()').string()
        grade_val = grade.xpath('count(.//i[@class="td-icon-star"])')
        if grade_name and grade_val:
            review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    pros = data.xpath('//div[@class="verdict-info-top plus"]/following-sibling::ul/li')
    if not pros:
        pros = data.xpath('(//h3[contains(., "Плюсы")]/following-sibling::ul)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).replace('•', '').replace(u'\uFEFF', '').strip()
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="verdict-info-top minus"]/following-sibling::ul/li')
    if not cons:
        cons = data.xpath('(//h3[contains(., "Минусы")]/following-sibling::ul)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).replace('•', '').replace(u'\uFEFF', '').strip()
        review.add_property(type='cons', value=con)

    summary = data.xpath('//meta[@name="description"]/@content').string()
    if summary:
        summary = summary.replace(u'\uFEFF', '')
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h1[contains(., "Выводы") or contains(., "Вердикт")]|//h2[contains(., "Подведем итоги") or contains(., "Краткий отзыв") or contains(., "Вывод")])/following-sibling::p[not(.//script or contains(., "Оценка в звездах") or strong[contains(., "Стоимость от") or contains(., "Характеристики") or contains(., "Плюсы") or contains(., "Минусы")])][normalize-space()]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="verdict-text"]//text()').string(multiple=True)
    if conclusion:
        conclusion.replace(u'\uFEFF', '')
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h1[contains(., "Выводы")]/preceding-sibling::p[not(script or contains(., "Оценка в звездах") or strong[contains(., "Стоимость от") or contains(., "Характеристики") or contains(., "Плюсы") or contains(., "Минусы")])][normalize-space()]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h1[contains(., "Часто задаваемые вопросы")]/preceding-sibling::p[not(script or contains(., "Оценка в звездах") or strong[contains(., "Стоимость от") or contains(., "Характеристики") or contains(., "Плюсы") or contains(., "Минусы")])][normalize-space()]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="article-part"]/p[not(script or contains(., "Оценка в звездах") or strong[contains(., "Стоимость от") or contains(., "Характеристики") or contains(., "Плюсы") or contains(., "Минусы")])][normalize-space()]//text()').string(multiple=True)

    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '').strip()
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        excerpt = excerpt.replace(u'\uFEFF', '')
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
