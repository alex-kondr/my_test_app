from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.giga.de/tech/tests/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//h2[@class='alice-teaser-title']/a[@class='alice-teaser-link']")
    for rev in revs:
        title = rev.xpath("text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    nexturl = data.xpath("//li[@class='pagination-next']/a/@href").string()
    if nexturl:
        session.queue(Request(nexturl), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' im Test')[0].split('im Alltagstest')[0].split(' von ')[0].split(':')[0].strip()
    product.ssid = context['url'].split('/')[-2]
    product.url = context['url']

    product.category = 'Technik'
    category = data.xpath('//span[@itemprop="name" and not(contains(., "GIGA") or contains(., "Tech") or contains(., "Sparen"))]/text()[string-length() < 15]').string()
    if category:
        product.category = category

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.ssid = product.ssid
    review.url = context['url']

    date = data.xpath("//time/@datetime").string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@title="Mehr von diesem Autor" and span]').first()
    if author:
        author_name = author.xpath(".//text()").string().replace(',', '').strip()
        author_url = author.xpath("@href").string()
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))

# https://www.giga.de/audio/beoplay-h4/tests/beoplay-h4-im-test-einstieg-ins-kabellose-luxussegment/
    grades = data.xpath('//p[contains(., "Einzelwertung")]/following-sibling::ul[1]/li')
    if not grades:
        grades = data.xpath('//h3[contains(., "Wertung im Detail")]/following-sibling::dl/dt')

    for grade in grades:
        if ':' in grade:
            name, grade = grade.xpath('text()').string().split(':')
            grade = grade.split()[0].strip()
            if '/' in grade:
                grade, best = grade.split('/')
                review.grades.append(Grade(name=name, value=float(grade)), best=float(best))
            else:
                review.grades.append(Grade(name=name, value=float(grade)), best=100.0)

# https://www.giga.de/test/oppo-watch-im-test-endlich-eine-apple-watch-fuer-android-nutzer/
    grade_overall = data.xpath("//div[@class='product-rating-rating']/strong//text()").string()
    if grade_overall:
        grade_overall = grade_overall.replace(',', '.')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    if not grade_overall:
        grade_overall = data.xpath('//strong[contains(., "Gesamt:")]//text()').string(multiple=True)
    if not grade_overall:
        grade_overall = data.xpath('//p[contains(., "Gesamt:")]//text()').string(multiple=True)
        if grade_overall:
            grade_overall = grade_overall.split('Prozent')[0].replace('Gesamt:', '').replace('Gesamt :', '').replace('(gerundet)', '').replace('%', '').replace(',', '.').strip()
            best = 100.0
            if '/' in grade_overall:
                grade_overall, best = grade_overall.split('/')

            review.grades.append(Grade(type='overall', value=float(grade_overall), best=float(best)))

    pros = data.xpath('//p[contains(., "Vorteile")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('text').string()
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[contains(., "Nachteile")]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('text()').string()
        review.add_property(type='pros', value=con)

    summary = data.xpath('//div[@data-init="toc-box"]/preceding-sibling::p/text()').string()
    if not summary:
        summary = data.xpath('//div[@data-init="product-box"]/preceding-sibling::p/text()').string()
    if not summary:
        summary = data.xpath('//div[@class="product-box-content"]/following-sibling::p[1]//text()').string()
    if not summary:
        summary = data.xpath('//div[contains(@class, "alice-layout-article-body")]/p//text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Persönliches Fazit:")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Spezifikationen") or figure)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Fazit:")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Facebook") or contains(., "Twitter") or figure)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="topic"]/p[not(contains(., "Vorteile:") or contains(., "Nachteile:") or contains(., "Gesamt"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//p[contains(., "Fazit:")]|//p[contains(., "Fazit:")]/following-sibling::p)//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace('Fazit:', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Persönliches Fazit:")]/preceding-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or figure)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Fazit:")]/preceding-sibling::p[not(contains(., "Euro UVP"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@data-init="toc-box"]/following-sibling::p[not(contains(., "Facebook") or contains(., "Twitter") or em)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="topic"]/following-sibling::p[not(contains(., "Facebook") or contains(., "Twitter") or em)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(., "Fazit:")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body//p[not(@class|figure|em or contains(., "Gesamt"))]//text()').string(multiple=True)

    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '')
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        review.add_property(type='excerpt', value=excerpt)
#############################
    product.reviews.append(review)

    session.emit(product)
