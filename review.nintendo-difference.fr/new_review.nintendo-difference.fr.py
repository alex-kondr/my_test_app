from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.nintendo-difference.com/test/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[contains(@class, "title")]')
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(name=name, url=url))

    next_url = data.xpath('//a[@class="next page-link"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.ssid = context['url'].split('/')[-2].replace('test-de-', '').replace('test-', '')
    product.manufacturer = data.xpath('//li[contains(., "Développeur")]/a/text()').string()
    product.category = 'Games'

    genre = data.xpath('//li[contains(., "Genre")]/a/text()').string()
    if genre:
        product.category += '|' + genre

    platforme = data.xpath('//li[contains(., "Support")]/a/text()').string()
    if platforme:
        product.category += '|' + platforme

    product.url = data.xpath('//a[contains(., "Site officiel")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[contains(@class, "title")]/text()').string()
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:modified_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="test-redacteur"]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//ul[contains(@class, "note-plus")]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[contains(@class, "note-moins")]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "verdict")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(@class, "test-conclusion")]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "verdict")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "review-content")]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
