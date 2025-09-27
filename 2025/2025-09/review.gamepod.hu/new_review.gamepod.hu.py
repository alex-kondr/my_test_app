from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://gamepod.hu/tesztek/index.html'), process_revlist, dict())


def process_revlist(data, context, session):
    for rev in data.xpath("//li[contains(@class, 'media')]"):
        category = rev.xpath(".//p[@class='content-info']//span[@class='badge']//text()").string()
        title = rev.xpath(".//h4[@class='media-heading']//a//text()").string()
        url = rev.xpath(".//a/@href").string()

        if url and title and category != 'Mobilarena':
            session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath("//li[@class='nav-arrow']/a[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' teszt ')[0].split(' beszámoló ')[0].split(' bemutató ')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Technika'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath("//meta[@property='article:published_time']/@content").string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("//li[contains(@class, 'mr-md-auto')]//a").first()
    if author:
        url = author.xpath("@href").string()
        name = author.xpath("span/text()").string(multiple=True)
        if url and name:
            review.authors.append(Person(name=name, ssid=name, profile_url=url))

    grade = data.xpath("//div[@class='content-body']//p//text()")
    if len(grade) > 1:
        grade = grade[-2].string()
        if grade != '' and re.search('^[0-9]*$', grade):
            review.grades.append(Grade(type='overall', value=float(grade), best=100.0))

    pros = data.xpath("//p[regexp:test(b/text(), 'Pro|pozitívumai|legjobb')]//following-sibling::ul[1]//li//text()")
    if not pros:
        pros = data.xpath("//p//b[contains(text(), 'Pro') or contains(text(), 'legjobb')]//parent::p//following-sibling::ul[1]//li//text()")
    if not pros:
        pros = data.xpath('//p[strong[contains(., "Ami tetszett:")]]/following-sibling::ul[1]/li//text()')

    for pro in pros:
        pro = pro.string()
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 2:
                review.add_property(type='pros', value=pro)

    cons = data.xpath("//p[regexp:test(b/text(), 'Kontra|leggyengébb|negatívumai')]//following-sibling::ul[1]//li//text()")
    if not cons:
        cons = data.xpath("//p//b[contains(text(), 'Kontra') or contains(text(), 'leggyengébb')]//parent::p//following-sibling::ul[1]//li//text()")
    if not cons:
        cons = data.xpath("//p[contains(text(), 'Pro') or contains(text(), 'legjobb')]//parent::p//following-sibling::ul[1]//following-sibling::ul[1]//li//text()")
    if not cons:
        cons = data.xpath("//p//b[contains(text(), 'Pro') or contains(text(), 'legjobb')]//parent::p//following-sibling::ul[1]//following-sibling::ul[1]//li//text()")
    if not cons:
        cons = data.xpath('//p[strong[contains(., "Ami nem tetszett:")]]/following-sibling::ul[1]/li//text()')

    for con in cons:
        con = con.string()
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 2:
                review.add_property(type='cons', value=con)

    summary = data.xpath("//p[@itemprop='description about']//text()").string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath("//p[regexp:test(b/text(), 'Összegzés:|Összefoglalás')]//following-sibling::p[1]//text()").string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath("//p[regexp:test(b/text(), 'Összegzés:|Összefoglalás')]//preceding-sibling::p[not(contains(., '[+]') or contains(., '[-]'))]//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//p[regexp:test(b/text(), 'Kontra|leggyengébb|negatívumai|Pro|pozitívumai|legjobb')]/preceding-sibling::p//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="content-body"]/p[not(regexp:test(., "Ami tetszett:|Ami nem tetszett:|Tételes értékelés:"))]//text()').string(multiple=True)

    pages = data.xpath('(//li[a[@data-toggle="dropdown"]])[1]/div/a')
    if pages and len(pages) > 1:
        for page in pages:
            title = page.xpath(".//text()").string()
            page_url = page.xpath("@href").string()
            review.add_property(type='pages', value=dict(url=page_url, title=title))

        session.do(Request(page_url), process_lastpage, dict(excerpt=excerpt, product=product, review=review))

    elif excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_lastpage(data, context, session):
    review = context['review']

    grade = data.xpath("//div[@class='content-body']//p//text()")
    if len(grade) > 1:
        grade = grade[-2].string()
        if grade != '' and re.search('^[0-9]*$', grade):
            review.grades.append(Grade(type='overall', value=float(grade), best=100.0))

    pros = data.xpath("//p[regexp:test(b/text(), 'Pro|pozitívumai|legjobb')]//following-sibling::ul[1]//li//text()")
    if not pros:
        pros = data.xpath("//p//b[contains(text(), 'Pro') or contains(text(), 'legjobb')]//parent::p//following-sibling::ul[1]//li//text()")
    if not pros:
        pros = data.xpath('//p[strong[contains(., "Ami tetszett:")]]/following-sibling::ul[1]/li//text()')

    for pro in pros:
        pro = pro.string()
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 2:
                review.add_property(type='pros', value=pro)

    cons = data.xpath("//p[regexp:test(b/text(), 'Kontra|leggyengébb|negatívumai')]//following-sibling::ul[1]//li//text()")
    if not cons:
        cons = data.xpath("//p//b[contains(text(), 'Kontra') or contains(text(), 'leggyengébb')]//parent::p//following-sibling::ul[1]//li//text()")
    if not cons:
        cons = data.xpath("//p[contains(text(), 'Pro') or contains(text(), 'legjobb')]//parent::p//following-sibling::ul[1]//following-sibling::ul[1]//li//text()")
    if not cons:
        cons = data.xpath("//p//b[contains(text(), 'Pro') or contains(text(), 'legjobb')]//parent::p//following-sibling::ul[1]//following-sibling::ul[1]//li//text()")
    if not cons:
        cons = data.xpath('//p[strong[contains(., "Ami nem tetszett:")]]/following-sibling::ul[1]/li//text()')

    for con in cons:
        con = con.string()
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 2:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[@class="content-body"]/p[not(regexp:test(., "Ami tetszett:|Ami nem tetszett:|Tételes értékelés:"))]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace('Pro:', '').replace('Kontra:', '').replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    if context['excerpt']:
        excerpt = context['excerpt'].replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
