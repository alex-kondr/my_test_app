from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('http://digiarena.e15.cz/testy'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="ar-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//div[@class="load-more-wrapper"]/a/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' (test)', '').replace(' [test]', '').replace('(recenze)', '').replace('(test objektivu)', '').replace('(video)', '').replace('Recenze: ', '').strip()
    product.url = context['url']
    product.ssid = data.xpath('//meta[@name="id"]/@content').string()

    product.category = data.xpath('//a[contains(@class, "article-tag") and not(contains(., "Příslušenství") or contains(., "Testy"))]/text()').string()
    if not product.category:
        product.category = 'Technologií'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//span[contains(@class, "article__date")]/text()').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="author"]/@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review-rating"]//text()').string()
    if grade_overall:
        grade_overall = grade_overall.split('/')[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[contains(@class, "review-block-plus")]/div[@class="items"]/div')
    if not pros:
        pros = data.xpath('(//h4|//p)[contains(., "Plusy")]/following-sibling::ul[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "review-block-minus")]/div[@class="items"]/div')
    if not cons:
        cons = data.xpath('(//h4|//p)[contains(., "Mínusy")]/following-sibling::ul[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="article__perex"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Závěr") or contains(., "Celkové hodnocení")]/following-sibling::p[not(contains(., "Specifikace") or preceding-sibling::p[contains(., "Plusy") or contains(., "Mínusy") or contains(., "Cena") or contains(., "Zdroj")] or contains(., "Plusy") or contains(., "Mínusy") or contains(., "Cena") or contains(., "Zdroj"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Závěr")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Závěr") or contains(., "Celkové hodnocení")]/preceding::div/p[not(@class or contains(., "technické parametry"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="article__body"]/p[not(contains(., "Specifikace"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "bodyPart")]/p[not(contains(., "Specifikace") or preceding-sibling::p[contains(., "Plusy") or contains(., "Mínusy") or contains(., "Cena") or contains(., "Zdroj")] or contains(., "Plusy") or contains(., "Mínusy") or contains(., "Cena") or contains(., "Zdroj") or contains(., "technické parametry"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
