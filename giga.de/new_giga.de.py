from agent import *
from models.products import *
import re

# URL = 'https://www.giga.de/laptops/dell-xps-15-2-in-1/tests/dell-xps-15-2-in-1-9575-im-test-4k-notebook-mit-intel-amd-kombiprozessor/'
def run(context, session):
    # session.queue(Request(URL), process_review, dict(url=URL, title='title'))
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
    product.name = context['title'].split(' im Test')[0].split('im Alltagstest')[0].replace('Test:', '').split(' von ')[0].split(':')[0].split(' im ')[0].strip()
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

# https://www.giga.de/test/oppo-watch-im-test-endlich-eine-apple-watch-fuer-android-nutzer/
    grade_overall = data.xpath("//div[@class='product-rating-rating']/strong//text()").string()
    if grade_overall:
        grade_overall = grade_overall.replace(',', '.')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    if not grade_overall:
        grade_overall = data.xpath('//p[strong[contains(., "Gesamt:")]]//text()').string(multiple=True)
    if not grade_overall:
        grade_overall = data.xpath('//strong[contains(., "Gesamt:")]//text()').string(multiple=True)
    if not grade_overall:
        grade_overall = data.xpath('//p[contains(., "Gesamt:")]//text()').string(multiple=True)
    if not grade_overall:
        grade_overall = data.xpath('//p[strong[contains(., "Wertung:") or contains(., "Gesamtwertung:")]]//text()').string(multiple=True)
    if not grade_overall:
        grade_overall = data.xpath('//strong[contains(., "Wertung:")]//text()').string(multiple=True)

    if grade_overall and not review.grades:
        grade_overall = grade_overall.split('Prozent')[0].split(':')[-1].replace('Gesamt:', '').replace('Gesamt :', '').replace('(gerundet)', '').replace('%', '').replace(',', '.').strip()
        best = 100
        if '/' in grade_overall:
            grade_overall, best = grade_overall.split('/')
            best = best.split()[0]

        review.grades.append(Grade(type='overall', value=float(grade_overall), best=float(best)))

# https://www.giga.de/audio/beoplay-h4/tests/beoplay-h4-im-test-einstieg-ins-kabellose-luxussegment/
# https://www.giga.de/laptops/dell-xps-15-2-in-1/tests/dell-xps-15-2-in-1-9575-im-test-4k-notebook-mit-intel-amd-kombiprozessor/
    grades = data.xpath('//p[contains(., "Einzelwertung")]/following-sibling::ul[1]/li//text()[contains(., ":")]').strings()
    if not grades:
        grades = data.xpath('//h3[contains(., "Wertung im Detail")]/following-sibling::dl/dt//text()[contains(., ":")]').strings()
    if not grades:
        grades = data.xpath('//h2[contains(., "Bewertung")]/following-sibling::ul[1]/li//text()[contains(., ":") and not(contains(., "Aber:"))]').strings()
    if not grades:
        grades = data.xpath('//h2[contains(., "Bewertung")]/following-sibling::ul[1]/li//text()[contains(., ":") and not(contains(., "Aber:"))]').strings()
# //*[regexp:test(text(), "\d/\d")][not(contains(., "@context") or contains(., "Gesamt:"))]
    for grade in grades:
        name, grade = grade.split(':')
        if re.search(r'^[\d, \s][0-9, /, \s][0-9, /, \s]?', grade):
            grade = grade.split()[0].replace(',', '.').strip()
            best = 100
            if '/' in grade:
                grade, best = grade.split('/')

            review.grades.append(Grade(name=name, value=float(grade), best=float(best)))

    if not grades:
        names = data.xpath('//h2[contains(., "Wertung")]/following-sibling::p[1]/strong/text()[not(contains(., "Wertung"))]').strings()
        grades = data.xpath('//h2[contains(., "Wertung")]/following-sibling::p[1]/text()').strings()
        if names and grades:
            names = [name.replace(':', '').strip() for name in names]
            for i, grade in enumerate(grades):
                grade, best = grade.split('/')
                review.grades.append(Grade(name=names[i], value=float(grade), best=float(best)))


    pros = data.xpath('//p[strong[contains(., "Vorteile")]]/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('//h3[contains(., "Vorteile")]/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('//strong[text()="Pro"]/following-sibling::ul/li')
    if not pros:
        pros = data.xpath('//p[strong[text()="Pro:"]]/following-sibling::ul[1]/li')

    for pro in pros:
        pro = pro.xpath('text').string()
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[strong[contains(., "Nachteile")]]/following-sibling::ul[1]/li[not(contains(., "/"))]')
    if not cons:
        cons = data.xpath('//h3[contains(., "Nachteile")]/following-sibling::ul[1]/li[not(contains(., "/"))]')
    if not cons:
        cons = data.xpath('//strong[text()="Kontra"]/following-sibling::ul/li')
    if not cons:
        cons = data.xpath('//p[strong[text()="Contra:"]]/following-sibling::ul[1]/li')

    for con in cons:
        con = con.xpath('text()').string()
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@data-init="toc-box"]/preceding-sibling::p/text()').string()
    if not summary:
        summary = data.xpath('//div[@data-init="product-box"]/preceding-sibling::p/text()').string()
    if not summary:
        summary = data.xpath('//div[@class="product-box-content"]/following-sibling::p[1]//text()').string()
    if not summary:
        summary = data.xpath('//div[contains(@class, "alice-layout-article-body")]/p//text()').string()

    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Persönliches Fazit:")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Spezifikationen") or contains(., "Facebook") or contains(., "Twitter") or figure)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Fazit:")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Facebook") or contains(., "Twitter") or figure)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="topic"]/p[not(contains(., "Wertung:") or contains(., "Pro:") or contains(., "Contra:") or contains(., "Gut zu wissen:") or contains(., "Vorteile:") or contains(., "Nachteile:") or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//p[contains(., "Fazit:")]|//p[contains(., "Fazit:")]/following-sibling::p[not(contains(., "Facebook") or contains(., "Twitter"))])//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="update"]/p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p/strong[contains(., "Mein persönliches Fazit")]/parent::p//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace('Fazit:', '').replace('Kurz-Fazit vorweg:', '').strip()
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
        excerpt = data.xpath('//div[@class="update"]/following-sibling::p[not(@class|figure|em or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body//p[not(@class|figure|em or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter"))]//text()').string(multiple=True)

    if excerpt and summary:
        excerpt = excerpt.replace(summary, '').strip()
    if excerpt and conclusion:
        excerpt = excerpt.replace(conclusion, '').strip()

    if excerpt and len(excerpt) > 10:
        review.add_property(type='excerpt', value=excerpt)
#############################
    product.reviews.append(review)

    session.emit(product)
