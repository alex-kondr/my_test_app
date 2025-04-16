import platform
from agent import *
from models.products import *


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.eurogamer.pt/reviews', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[contains(@class, "link link--expand")]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[span[@aria-label="Próxima página"]]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.manufacturer = data.xpath('//li[strong[contains(., "Estúdio:")]]/text()').string()

    name = data.xpath('//aside[@class="aside right"]/h2/text()').string()
    if name:
        product.name = name
    else:
        product.name = context['title'].split('review -')[0].replace(' review', '').strip()

    platforms = data.xpath('//li[strong[contains(., "Disponível para:")]]/text()').string()
    if platforms:
        product.category = 'Jogos' + '|' + platforms.replace(', ', '/')
    else:
        product.category = 'Jogos'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="author"]/a/text()').string()
    author_url = data.xpath('//span[@class="author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review_rating"]/@data-value').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('//td[font[@color="#169600"]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//td[font[@color="#E10000"]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="strapline"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Conclusão")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "body_content")]/div[not(@class)]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusão")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "body_content")]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
