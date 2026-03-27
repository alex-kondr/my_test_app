from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.220volt.hu/Teszt'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "item__title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(., "Next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' teszt – ')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('-teszt', '')
    product.category = 'Photography'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//span[@class="blog-date"]/text()').string()

    author = data.xpath('//p[contains(text(), "Írta és")]/a/text()').string()
    author_url = data.xpath('//p[contains(text(), "Írta és")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('(//h3[contains(., "pozitívumai")]/following-sibling::*)[1]/li')
    if not pros:
         pros = data.xpath('(//p[contains(., "Pros")]/following-sibling::*)[1]/li')
    if not pros:
         pros = data.xpath('(//p[contains(., "pozitívumai")]/following-sibling::*)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//h3[contains(., "pozitívumai")]/following-sibling::p[starts-with(normalize-space(text()), "+")]/text()[normalize-space(.)]')
        for pro in pros:
            pro = pro.string(multiple=True)
            if pro:
                pro = pro.strip(' +-*.:;•,–')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[contains(., "negatívumai")]/following-sibling::*)[1]/li')
    if not cons:
         cons = data.xpath('(//p[contains(., "Cons")]/following-sibling::*)[1]/li')
    if not cons:
         cons = data.xpath('(//p[contains(., "negatívumai")]/following-sibling::*)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//h3[contains(., "negatívumai")]/following-sibling::p[starts-with(normalize-space(text()), "-")]/text()')
        for con in cons:
            con = con.string(multiple=True)
            if con:
                con = con.strip(' +-*.:;•,–')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "blog-details__intro")]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "röviden") or contains(., "Röviden")]/following-sibling::p[not(contains(.,"számodra:") or contains(.,"Pros") or contains(.,"Cons") or contains(.,"Pro/Con") or contains(.,"pozitívumai") or contains(.,"negatívumai"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "siteblock_text") or contains(@class, "blog-details__text") or contains(@class, "page_txt")]/p[not(contains(.,"számodra:") or contains(.,"Pros") or contains(.,"Cons") or contains(.,"Pro/Con") or contains(.,"pozitívumai") or contains(.,"negatívumai") or preceding::h3[contains(., "röviden") or contains(., "Röviden")])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
