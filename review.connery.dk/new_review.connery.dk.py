from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://connery.dk/tag/test/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "post") and h3]')
    for rev in revs:
        title = rev.xpath('h3/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Test: ', '').replace('TEST: ', '').replace('Kreativ test: ', '').split(' – ')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('test-', '')

    category = data.xpath('//div[h1]/a/text()').string()
    if category:
        product.category = category.replace(' Testzone', '').strip()
    else:
        product.category = 'Teknologi'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@href, "https://connery.dk/redaktoer/")]/text()').string()
    author_url = data.xpath('//a[contains(@href, "https://connery.dk/redaktoer/")]/@href').string()
    if author and author_url:
        author_url = author_url.split('+')[-1]
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[contains(., "ud af 6 stjerner")]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.split(' ud af ')[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=6.0))

    pros = data.xpath('//p[contains(., "Hvad fungerer virkelig godt?")]/strong[not(contains(., "Hvad fungerer virkelig godt?"))]')
    for i, pro in enumerate(pros, start=2):
        pro = pro.xpath('text()|following-sibling::*[count(preceding-sibling::strong)={i} and not(self::strong)]//text()|following-sibling::text()[count(preceding-sibling::strong)={i}]'.format(i=i)).string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//blockquote[p[contains(., "Fordele:")]]/p[not(regexp:test(., "Fordele:|Ulemper:") or preceding-sibling::p[contains(., "Ulemper:")])]')
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            if pro:
                pro = pro.strip(' +-*.:;•,–')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[contains(., "Hvad kunne være bedre?")]/strong[not(contains(., "Hvad kunne være bedre?"))]')
    for i, con in enumerate(cons, start=2):
        con = con.xpath('text()|following-sibling::*[count(preceding-sibling::strong)={i} and not(self::strong)]//text()|following-sibling::text()[count(preceding-sibling::strong)={i}]'.format(i=i)).string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//p[contains(., "Ulemper:")]/following-sibling::p[not(contains(., "Ulemper:"))]')
        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            if con:
                con = con.strip(' +-*.:;•,–')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "post-excerpt")]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[contains(., "Konklusion: ")]//text()[not(contains(., "Konklusion:") or @style)]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[contains(., "Konklusion: ")]/preceding-sibling::p[not(regexp:test(., "Hvad fungerer virkelig godt\?|Hvad kunne være bedre\?|Pris og tilgængelighed|6 stjerner") or @style or preceding::p[contains(., "Pris og tilgængelighed")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(regexp:test(., "Hvad fungerer virkelig godt\?|Hvad kunne være bedre\?|Pris og tilgængelighed|6 stjerner") or @style or preceding::p[contains(., "Pris og tilgængelighed")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
