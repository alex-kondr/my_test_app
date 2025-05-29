from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.macworld.se/tester', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    title = data.xpath('//h1[@class="entry-title"]//text()').string(multiple=True)

    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Tech'
    product.manufacturer = data.xpath('//strong[contains(., "Tillverkare")]/following-sibling::a[1]/text()').string()

    product.name = data.xpath('//strong[contains(text(), "Produktnamn:")]/following-sibling::text()[1]').string()
    if not product.name:
        product.name = title.split(' – ')[0].replace('Test Procamera: ', '').replace('Minitest: ', '').replace('Test: ', '').replace('TEST: ', '').replace('Hårdtest: ', '').replace('Testfavorit!', '').replace('Långtidstest:', '').replace('Långtest: ', '').replace('Stort test:', '').replace('Vi testar nya ', '').replace('Vi testar ', '').replace('Test ', '').replace(' test', '').strip().title()

    prod_url = data.xpath('//a[contains(., "Till butik")]/@href').string()
    platform = data.xpath('//strong[contains(., "Plattform")]/following-sibling::p[1]/text()').string()
    if prod_url and platform:
        product.url = prod_url + '|' + platform
    elif prod_url:
        product.url = prod_url
    elif platform:
        product.url = platform

    category = data.xpath('//div[@class="single-breadcrumb"]/a[not(regexp:test(., "Hem|tester"))]/text()').string()
    if category:
        product.category = category.strip(' /')

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author = author.split(':')[-1].strip()
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        author = author.split(':')[-1].strip()
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="starRating"]/@style').string()
    if grade_overall:
        grade_overall = grade_overall.split()[-1].strip(' ;')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('//h3[contains(., "Fördelar")]/following-sibling::ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//h3[contains(., "Nackdelar")]/following-sibling::ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="subheadline"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "Summa summarum|Slutsats|Köpa eller inte köpa")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[contains(., "Omdöme")]/following-sibling::p[1]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Summa summarum|Slutsats|Köpa eller inte köpa")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body/p//text()').string(multiple=True)
    if not excerpt or len(excerpt) < 20:
        excerpt = data.xpath('//div[@class="legacy_content"]/*[not(@class or @id or self::ul or self::script)]//text()|//div[@class="legacy_content"]/text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
