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
    product.name = context['title'].split(' im Test')[0].split('im Alltagstest')[0].split('Test - ')[0].replace('Review:', '').replace('Test:', '').split(' von ')[0].split(':')[0].split(' im ')[0].strip()
    product.ssid = context['url'].split('/')[-2]
    product.url = context['url']

    product_url = data.xpath('//div[@class="text-center" and .//span[@class="btn-download-maintext"]]/a/@href').string()
    if not product_url:
        product_url = data.xpath('//p[strong[contains(., "Links")]]/following-sibling::ul[1]/li//a/@href').string()
    if not product_url:
        product_url = data.xpath('//a[@data-merchant="amazon"]/@href').string()
    if product_url:
        product.url = product_url

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

    grade_overall = data.xpath("//div[@class='product-rating-rating']/strong//text()").string()
    if grade_overall:
        grade_overall = grade_overall.replace(',', '.')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    if not grade_overall:
        grade_overall = data.xpath('//p[strong[contains(., "Gesamt:")]]//text()[contains(., "Gesamt")]').string(multiple=True)
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
        try:
            grade_overall = float(grade_overall)
            if grade_overall // 20 == grade_overall / 20:
                grade_overall /= 20
                best = 5
            review.grades.append(Grade(type='overall', value=grade_overall, best=float(best)))
        except ValueError:
            pass

    grades = data.xpath('//*[regexp:test(text(), ": \d/\d\d?$")][not(contains(., "@context") or contains(., "Gesamt:"))]')
    for grade in grades:
        name, grade = grade.xpath('text()').string().split(':')
        grade, best = grade.split('/')
        review.grades.append(Grade(name=name, value=float(grade), best=float(best)))

    grades = data.xpath('(//*[regexp:test(text(), "^[^:]+: \d\d Prozent")][not(contains(., "@context") or contains(., "Gesamt"))]/parent::ul)[last()]/li//text()[not(contains(., "Gesamt:"))]').strings()
    if not grades:
        grades = data.xpath('//*[regexp:test(text(), "^[^:]+: \d\d Prozent")][not(contains(., "@context") or contains(., "Gesamt"))]/text()[not(contains(., "Gesamt:"))]').strings()
    for grade in grades:
        name, grade = grade.split(':')
        name = name.strip()
        grade = grade.split()[0]
        review.grades.append(Grade(name=name, value=float(grade), best=100.0))

    pros = data.xpath('//li[@class="arg-pro"]')
    if not pros:
        pros = data.xpath('//p[strong[contains(., "Vorteile") and contains(., "+")]]')
    if not pros:
        pros = data.xpath('//p[strong[contains(., "Vorteile")]]/following-sibling::ul[1]/li[not(.//a)]')
    if not pros:
        pros = data.xpath('//h3[contains(., "Vorteile")]/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('//h3[.//strong[contains(., "Pro")]]/following-sibling::ul[1]/li[string-length() > 2]')
    if not pros:
        pros = data.xpath('//strong[text()="Pro"]/following-sibling::ul/li')
    if not pros:
        pros = data.xpath('//p[strong[text()="Pro:"]]/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('//h2[contains(., "Das hat uns gut gefallen")]/following-sibling::ul/li[not(@class)]')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).replace('+', '').strip()
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//li[@class="arg-con"]')
    if not cons:
        cons = data.xpath('//p[strong[contains(., "Nachteile")]][contains(., "-")]')
    if not cons:
        cons = data.xpath('//p[strong[contains(., "Nachteile")]]/following-sibling::ul[1]/li[not(contains(., "/") or contains(., "Prozent") or .//a)]')
    if not cons:
        cons = data.xpath('//h3[contains(., "Nachteile")]/following-sibling::ul[1]/li[not(contains(., "/") or contains(., "Prozent"))]')
    if not cons:
        cons = data.xpath('//h3[.//strong[contains(., "Contra")]]/following-sibling::ul[1]/li[string-length() > 2]')
    if not cons:
        cons = data.xpath('//strong[text()="Kontra"]/following-sibling::ul/li')
    if not cons:
        cons = data.xpath('//p[strong[text()="Contra:"]]/following-sibling::ul[1]/li')
    if not cons:
        cons = data.xpath('//h2[contains(., "Das hat uns nicht so gut gefallen")]/following::ul[1]/li[not(@class)]')

    if pros:
        for con in cons:
            con = con.xpath('.//text()').string(multiple=True).replace('-', '').strip()
            review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@data-init="toc-box"]/preceding-sibling::p//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//div[@data-init="product-box"]/preceding-sibling::p//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//div[@class="product-box-content"]/following-sibling::p[1]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//div[contains(@class, "alice-layout-article-body")]/p//text()').string(multiple=True)

    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Persönliches Fazit:")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Spezifikationen") or contains(., "Facebook") or contains(., "Twitter") or figure)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Fazit")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Facebook") or contains(., "Twitter") or figure or contains(., "wertung") or contains(., "US-Dollar") or contains(., "nicht gefallen"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Fazit zur")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Facebook") or contains(., "Twitter") or figure)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Testfazit")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Facebook") or contains(., "Twitter") or contains(., "Preis") or contains(., "Links") or contains(., "für die Unterstützung!") or figure)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="topic"]/p[not(contains(., "Wertung:") or contains(., "Pro:") or contains(., "Contra:") or contains(., "Gut zu wissen:") or contains(., "Vorteile:") or contains(., "Nachteile:") or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//p[contains(., "Fazit:")]|//p[contains(., "Fazit:")]/following-sibling::p[not(contains(., "Facebook") or contains(., "Twitter") or contains(., "Disclosure:") or (contains(., "Gesamt")))])//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="update"]/p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p/strong[contains(., "Mein persönliches Fazit")]/parent::p//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace('Fazit:', '').replace('Kurz-Fazit vorweg:', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Persönliches Fazit:")]/preceding-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or figure)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Fazit")]/preceding-sibling::p[not(contains(., "Euro UVP"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Fazit zur")]/preceding-sibling::p[not(contains(., "Euro UVP"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Testfazit")]/preceding-sibling::p[not(contains(., "Euro UVP"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@data-init="toc-box"]/following-sibling::p[not(contains(., "Facebook") or contains(., "Twitter") or em)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(., "Fazit:")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="topic"]/following-sibling::p[not(contains(., "Facebook") or contains(., "Twitter") or em)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="update"]/following-sibling::p[not(@class|figure|em or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter"))]//text()').string(multiple=True)
    if not excerpt and not conclusion:
        excerpt = data.xpath('//p[@class="p1"][not(contains(., "Nächste Seite:"))]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//body//p[not(@class|figure or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter"))]//text()').string(multiple=True)

    if excerpt and summary:
        excerpt = excerpt.replace(summary, '').strip()
    if excerpt and conclusion:
        excerpt = excerpt.replace(conclusion, '').strip()

    context['product'] = product
    context['conclusion'] = conclusion
    context['excerpt'] = excerpt

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        review.add_property(type='pages', value=dict(title=review.title + ' - page 1', url=context['url']))
        session.do(Request(next_url), process_review_next, dict(context, review=review, url=next_url, page=2))
    else:
        context['review'] = review
        context['page'] = 1

        process_review_next(data, context, session)


def process_review_next(data, context, session):
    review = context['review']
    conclusion = context['conclusion']

    page = context['page']
    if page > 1:
        review.add_property(type="pages", value=dict(title=review.title+' - page '+str(page), url=context["url"]))

        pros = data.xpath('//li[@class="arg-pro"]')
        if not pros:
            pros = data.xpath('//p[strong[contains(., "Vorteile") and contains(., "+")]]')
        if not pros:
            pros = data.xpath('//p[strong[contains(., "Vorteile")]]/following-sibling::ul[1]/li[not(.//a)]')
        if not pros:
            pros = data.xpath('//h3[contains(., "Vorteile")]/following-sibling::ul[1]/li')
        if not pros:
            pros = data.xpath('//h3[.//strong[contains(., "Pro")]]/following-sibling::ul[1]/li[string-length() > 2]')
        if not pros:
            pros = data.xpath('//strong[text()="Pro"]/following-sibling::ul/li')
        if not pros:
            pros = data.xpath('//p[strong[text()="Pro:"]]/following-sibling::ul[1]/li')
        if not pros:
            pros = data.xpath('//h2[contains(., "Das hat uns gut gefallen")]/following-sibling::ul/li[not(@class)]')

        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True).replace('+', '').strip()
            review.add_property(type='pros', value=pro)

        cons = data.xpath('//li[@class="arg-con"]')
        if not cons:
            cons = data.xpath('//p[strong[contains(., "Nachteile")]][contains(., "-")]')
        if not cons:
            cons = data.xpath('//p[strong[contains(., "Nachteile")]]/following-sibling::ul[1]/li[not(contains(., "/") or contains(., "Prozent") or .//a)]')
        if not cons:
            cons = data.xpath('//h3[contains(., "Nachteile")]/following-sibling::ul[1]/li[not(contains(., "/") or contains(., "Prozent"))]')
        if not cons:
            cons = data.xpath('//h3[.//strong[contains(., "Contra")]]/following-sibling::ul[1]/li[string-length() > 2]')
        if not cons:
            cons = data.xpath('//strong[text()="Kontra"]/following-sibling::ul/li')
        if not cons:
            cons = data.xpath('//p[strong[text()="Contra:"]]/following-sibling::ul[1]/li')
        if not cons:
            cons = data.xpath('//h2[contains(., "Das hat uns nicht so gut gefallen")]/following::ul[1]/li[not(@class)]')

        if pros:
            for con in cons:
                con = con.xpath('.//text()').string(multiple=True).replace('-', '').strip()
                review.add_property(type='cons', value=con)

        if not conclusion:
            conclusion = data.xpath('//h3[contains(., "Persönliches Fazit:")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Spezifikationen") or contains(., "Facebook") or contains(., "Twitter") or figure)]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//h2[contains(., "Fazit")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Facebook") or contains(., "Twitter") or figure or contains(., "wertung") or contains(., "US-Dollar") or contains(., "nicht gefallen"))]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//h2[contains(., "Fazit zur")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Facebook") or contains(., "Twitter") or figure)]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//h2[contains(., "Testfazit")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Facebook") or contains(., "Twitter") or contains(., "Preis") or contains(., "Links") or contains(., "für die Unterstützung!") or figure)]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//div[@class="topic"]/p[not(contains(., "Wertung:") or contains(., "Pro:") or contains(., "Contra:") or contains(., "Gut zu wissen:") or contains(., "Vorteile:") or contains(., "Nachteile:") or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter"))]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('(//p[contains(., "Fazit:")]|//p[contains(., "Fazit:")]/following-sibling::p[not(contains(., "Facebook") or contains(., "Twitter") or contains(., "Disclosure:") or (contains(., "Gesamt")))])//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//div[@class="update"]/p//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//p/strong[contains(., "Mein persönliches Fazit")]/parent::p//text()').string(multiple=True)

        if conclusion:
            conclusion = conclusion.replace('Fazit:', '').replace('Kurz-Fazit vorweg:', '').strip()
            review.add_property(type='conclusion', value=conclusion)

        excerpt = data.xpath('//h3[contains(., "Persönliches Fazit:")]/preceding-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or figure)]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//h2[contains(., "Fazit")]/preceding-sibling::p[not(contains(., "Euro UVP"))]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//h2[contains(., "Fazit zur")]/preceding-sibling::p[not(contains(., "Euro UVP"))]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//h2[contains(., "Testfazit")]/preceding-sibling::p[not(contains(., "Euro UVP"))]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[@data-init="toc-box"]/following-sibling::p[not(contains(., "Facebook") or contains(., "Twitter") or em)]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//p[contains(., "Fazit:")]/preceding-sibling::p//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[@class="topic"]/following-sibling::p[not(contains(., "Facebook") or contains(., "Twitter") or em)]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[@class="update"]/following-sibling::p[not(@class|figure|em or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter"))]//text()').string(multiple=True)
        if not excerpt and not conclusion:
            excerpt = data.xpath('//p[@class="p1"][not(contains(., "Nächste Seite:"))]//text()').string(multiple=True)
            if not excerpt:
                excerpt = data.xpath('//body//p[not(@class|figure or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter"))]//text()').string(multiple=True)

        if excerpt and len(excerpt) > 10:
            context['excerpt'] += ' ' + excerpt

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.do(Request(next_url), process_review_next, dict(context, review=review, conclusion=conclusion, url=next_url, page=page + 1))

    elif context['excerpt'] and len(context['excerpt']) > 10:
        product = context['product']

        review.add_property(type="excerpt", value=context['excerpt'])

        product.reviews.append(review)

        session.emit(product)
