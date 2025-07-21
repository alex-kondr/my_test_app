from agent import *
from models.products import *


XCAT = ['Аналитика и полезная информация']


def run(context, session):
    session.queue(Request('https://www.ixbt.com/mobilepc/', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="filter_wrapper"]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//a[contains(@class, "title")]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[text()="»"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('//th[@colspan="3"]//text()').string() or context['title']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.shtml', '').replace('.html', '').replace('-review', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@itemprop="datePublished"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    authors = data.xpath('//p[@class="author"]')
    for author in authors:
        author_name = author.xpath('.//text()').string(multiple=True)
        author_url = author.xpath('a/@href').string()
        if author_name and author_url:
            author_ssid = author_url.split('/')[-2]
            review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

    pros = data.xpath('(//*[regexp:test(.,"Плюсы|Достоинства")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//*[regexp:test(.,"Минусы|Недостатки")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h3[regexp:test(.,"Вывод|Итог|Заключение")]/following-sibling::p[not(@class or regexp:test(.,"Плюсы|Достоинства|Минусы|Недостатки|В заключение предлагаем посмотреть") or preceding::*[contains(., "Добавить комментарий") or @name="comments"])]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[regexp:test(.,"Вывод|Итог|Заключение")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content")]/p[not(@class or regexp:test(.,"Плюсы|Достоинства|Минусы|Недостатки|В заключение предлагаем посмотреть") or preceding::*[contains(., "Добавить комментарий") or @name="comments"])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
