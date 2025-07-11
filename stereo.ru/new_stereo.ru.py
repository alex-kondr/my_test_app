from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://stereo.ru/tests', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[contains(@class, "title")]')
    for rev in revs:
        title = rev.xpath('span[contains(@class, "title")]/text()').string()
        url = rev.xpath('@href').string()

        if title:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.ssid = context['url'].split('/')[-1]
    product.category = data.xpath('//a[contains(@class, "relation_channel")]/text()').string() or 'Tech'

    product.url = data.xpath('//div[label[contains(., "Официальный сайт")]]//a/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content|//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "username_author")]/span[@class="username__name"]/text()').string()
    author_url = data.xpath('//a[contains(@class, "username_author")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].replace('@', '')
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//div[label[contains(., "Достоинства")]]/div/p')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1 and pro != 'нет':
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[label[contains(., "Недостатки")]]/div/p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1 and con != 'нет':
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@itemprop="description"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2[contains(., "Выводы")]|//p[strong[contains(., "Выводы")]])/following-sibling::p[not(preceding-sibling::h2[contains(., "Музыкальный материал")])]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2[contains(., "Выводы")]|//p[strong[contains(., "Выводы")]])/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="app__body"]/p[not(preceding-sibling::h2[contains(., "Музыкальный материал")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
