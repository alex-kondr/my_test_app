from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://prohardver.hu/tesztek/index.html', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h4/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' teszt', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]

    cats = data.xpath('//ol[@class="breadcrumb"]/li[not(regexp:test(., "Tesztek|Hazai Pálya|Hírek"))]//text()[normalize-space()]').strings()
    if len(cats) > 1:
        product.category = cats[0] + '|' + '/'.join(cats[1:])
    elif cats:
        product.category = cats[0]
    else:
        product.category = 'Technologia'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if not date:
        date = data.xpath('//li[time[contains(@itemprop, "datePublished")]]/text()').string(multiple=True)

    if date:
        review.date = date.split('T')[0].split()[0]

    author = data.xpath('//a[@rel="author"]//text()').string(multiple=True)
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].replace('.html', '')
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('(//p[b[contains(., "pozitívumai")]]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p[b[contains(., "hiányosságai")]]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[contains(@itemprop, "description")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[b[contains(., "Összefoglalás")]]/following-sibling::p[not(b[regexp:test(., "pozitívumai|hiányosságai")])]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    context['excerpt'] = data.xpath('//p[b[contains(., "Összefoglalás")]]/preceding-sibling::p//text()').string(multiple=True)
    if not context['excerpt']:
        context['excerpt'] = data.xpath('//div[@class="content-body"]/p[not(b[regexp:test(., "pozitívumai|hiányosságai")])]//text()').string(multiple=True)

    context['product'] = product

    pages = data.xpath('//li[@class="list-inline-item dropdown d-flex"]//a[@class="dropdown-item"]')
    if len(pages) > 1:
        for page in pages:
            title = page.xpath('text()').string()
            page_url = page.xpath('@href').string()
            review.add_property(type='pages', value=dict(title=title , url=page_url))

        session.do(Request(page_url, use='curl', force_charset='utf-8'), process_review_last, dict(context, review=review, last_page=True))

    else:
        context['review'] = review

        process_review_last(data, context, session)


def process_review_last(data, context, session):
    review = context['review']

    if context.get('last_page'):
        pros = data.xpath('(//p[b[contains(., "pozitívumai")]]/following-sibling::*)[1]/li')
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            if pro:
                pro = pro.strip(' +-*.;•–')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

        cons = data.xpath('(//p[b[contains(., "hiányosságai")]]/following-sibling::*)[1]/li')
        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            if con:
                con = con.strip(' +-*.;•–')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

        conclusion = data.xpath('//div[@class="content-body"]/p[not(b[regexp:test(., "pozitívumai|hiányosságai")])]//text()').string(multiple=True)
        if conclusion:
            review.add_property(type='conclusion', value=conclusion)

    if context['excerpt']:
        review.add_property(type='excdrpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
