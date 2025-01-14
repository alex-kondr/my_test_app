from agent import *
from models.products import *


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://i2hard.ru/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="feed__heading h4"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@id="_next_page"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.name = context['title']

    product.category = data.xpath('//div[@class="info__subcategories-item"]/a/text()').string()
    if not product.category:
        product.category = 'Технологии'

    review = Review()
    review.type = 'pro'
    review.title =context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//div[@class="info__date info__date_bullet"]/text()').string()

    author = data.xpath('//div[@class="info__author"]/a/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('(//h4[contains(., "Плюсы:")]|//h4[contains(., "Преимущества")]|//p[strong[contains(., "Достоинства:")]])/following-sibling::div[@class="sp-lists"][1]/ul/li[normalize-space()]')
    if not pros:
        pros = data.xpath('(//span[contains(., "Плюсы:")]|//p[contains(., "Плюсы:") or contains(., "Достоинства")]|//h4[contains(., "Достоинства")]|//b[contains(., "Достоинства")])/following-sibling::ul[1]/li[normalize-space()]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip('.;')
        review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h4[contains(., "Минусы:")]|//h4[contains(., "Недостатки")]|//p[strong[contains(., "Недостатки:")]])/following-sibling::div[@class="sp-lists"][1]/ul/li[normalize-space()]')
    if not cons:
        cons = data.xpath('(//span[contains(., "Минусы:")]|//p[contains(., "Минусы:") or contains(., "Недостатки")]|//h4[contains(., "Недостатки")]|//b[contains(., "Недостатки") or contains(., "недочеты")])/following-sibling::ul[1]/li[normalize-space()]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip('.;')
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="article__subheading"]//text()').string(multiple=True)
    if summary and '…' not in summary:
        summary = summary.replace(u'\uFEFF', '')
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2[contains(., "Итоги") or contains(., "Заключение") or contains(., "Вывод")]/following-sibling::p[not(contains(., "Плюсы") or contains(., "Минусы") or contains(., "получает награду"))]//text()|//h2[contains(., "Итоги") or contains(., "Заключение") or contains(., "Вывод")]/following-sibling::text())[not(contains(., "Автор статьи") or contains(., "Средняя цена") or contains(., "Недостатки:"))]').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '')
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Итоги") or contains(., "Заключение") or contains(., "Вывод")]/preceding-sibling::p//text()|//h2[contains(., "Итоги") or contains(., "Заключение") or contains(., "Вывод")]/preceding-sibling::text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="article__text"]/p//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').replace(summary, '')

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
