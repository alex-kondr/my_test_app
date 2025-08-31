from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.recordere.dk/tests/', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath("text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(" – ")[0].replace('MINI-TEST: ', '').replace('TEST: ', '').replace('Test: ', '').replace('test: ', '').replace('SLUT: ', '').replace('Spilanmeldelse: ', '').replace('TEST ', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('test-', '')
    product.category = 'Teknologi'

    product.url = data.xpath('//a[contains(., "Pricerunner")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    authors = data.xpath("//div[@class='td-post-author-name']/a")
    for author in authors:
        author_name = author.xpath(".//text()").string()
        author_url = author.xpath("@href").string()
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_ssid))

    grade_overall = data.xpath("//div[@class='td-review-final-score']/text()[regexp:test(., '\d')]").string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    if not grade_overall:
        grade_overall = data.xpath("//div[@class[regexp:test(., 'score__wrap__with__title')]]//div[@class='score']/text()[regexp:test(., '\d')]").string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath("//div[@class='lets-review-block__pros']/div[@class[regexp:test(., 'review-block__pro')]]")
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.replace('N/A', '').strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath("//div[@class='lets-review-block__cons']/div[@class[regexp:test(., 'review-block__con')]]")
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.replace('N/A', '').strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath("//div[@class='td-review-summary-content']//text()[string-length(normalize-space(.))>0]").string()
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h4[regexp:test(., "Konklusion")][last()]/following-sibling::p[not(regexp:test(., "Karakter:|Pris:|Score \d") or preceding-sibling::h4[contains(., "Pris")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h4[contains(., "Samlet set")][last()]/following-sibling::p[not(regexp:test(., "Karakter:|Pris:|Score \d") or preceding-sibling::h4[contains(., "Pris")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[regexp:test(., "Konklusion")][last()]/following-sibling::p[not(regexp:test(., "Karakter:|Pris:|Score \d") or preceding-sibling::h3[contains(., "Pris")])]//text()').string(multiple=True)

    if conclusion and not summary:
        summary = data.xpath('//div[@class="lets-review-block__conclusion"]//text()').string(multiple=True)
        if summary:
            review.add_property(type='summary', value=summary)

            conclusion = conclusion.replace(summary, '').strip()

    if not conclusion:
        conclusion = data.xpath('//div[@class="lets-review-block__conclusion"]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h4[regexp:test(., "Konklusion")]/preceding-sibling::p[not(regexp:test(., "Karakter:|Pris:|Score \d"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h4[contains(., "Samlet set")]/preceding-sibling::p[not(regexp:test(., "Karakter:|Pris:|Score \d"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h3[regexp:test(., "Konklusion")]/preceding-sibling::p[not(regexp:test(., "Karakter:|Pris:|Score \d"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="content_text"]/p[not(regexp:test(., "Karakter:|Pris:|Score \d"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
