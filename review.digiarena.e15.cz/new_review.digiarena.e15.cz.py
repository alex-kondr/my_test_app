from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('http://digiarena.e15.cz/testy'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="ar-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('(//div[@class="load-more-wrapper"]|//span[@class="next"])/a/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    revs = data.xpath('//div[contains(@class, "bodyPart")]/h3[regexp:test(., "^\d+. ")]')
    if revs:
        process_reviews(data, context, session)
        return

    product = Product()
    product.name = context['title'].split(': Test')[0].split(': test')[0].split('test:')[-1].replace(': Preview Extractor', '').replace('Test bezzrcadlovky', '').replace('Test objektivu', '').replace('(test)', '').replace('[test]', '').replace(' v testu', '').replace(u'(test \u010dte\u010dek karet)', '').replace('(test stativu)', '').replace(u'(test stativ\u016f)', '').replace(u'(test kinofilmov\u00e9ho skeneru)', '').replace(u'(test skener\u016f Epson V700 a V750)', '').replace('(recenze)', '').replace('(test objektivu)', '').replace('(video)', '').replace('Recenze: ', '').replace('Test: ', '').replace(' test', '').replace('Test ', '').strip()
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

    pros = data.xpath('(//h4|//h3|//p)[contains(., "Plusy") or contains(., "Klady") and contains(., "+")]/text()')
    for pro in pros:
        pro = pro.string().strip(' -+')
        review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//div[contains(@class, "review-block-plus")]/div[@class="items"]/div')
        if not pros:
            pros = data.xpath('(//h4|//h3|//p)[contains(., "Plusy") or contains(., "Klady")]/following-sibling::ul[1]/li')

        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h4|//h3|//p)[(contains(., "Mínusy") or contains(., "Zápory")) and contains(., "-")]/text()')
    for con in cons:
        con = con.string().strip(' -+')
        review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//div[contains(@class, "review-block-minus")]/div[@class="items"]/div')
        if not cons:
            cons = data.xpath('(//h4|//h3|//p)[contains(., "Mínusy") or contains(., "Zápory")]/following-sibling::ul[1]/li')

        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="article__perex"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2|//h3)[contains(., "Závěr") or contains(., "Celkové hodnocení") or contains(., "Verdikt")]/following-sibling::p[not(contains(., "Specifikace") or preceding-sibling::p[contains(., "Plusy") or contains(., "Mínusy") or contains(., "Cena") or contains(., "Zdroj")] or contains(., "Plusy") or contains(., "Mínusy") or contains(., "Cena") or contains(., "Zdroj"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Závěr")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//h2|//h3)[contains(., "Závěr") or contains(., "Celkové hodnocení") or contains(., "Verdikt")]/preceding::p[not(@class or contains(., "technické parametry") or contains(., "Specifikace"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="article__body"]/p[not(contains(., "Specifikace"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "bodyPart")]/p[not(contains(., "Specifikace") or preceding-sibling::p[contains(., "Plusy") or contains(., "Mínusy") or contains(., "Cena") or contains(., "Zdroj")] or contains(., "Plusy") or contains(., "Mínusy") or contains(., "Cena") or contains(., "Zdroj") or contains(., "technické parametry"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_reviews(data, context, session):
    revs = data.xpath('//div[contains(@class, "bodyPart")]/h3[regexp:test(., "^\d+. ")]')
    for i, rev in enumerate(revs, start=1):
        product = Product()
        product.name = rev.xpath('text()').string().split(' ', 1)[-1].strip()
        product.url = context['url']
        product.ssid = product.name.lower().replace(' ', '_')

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

        grades = rev.xpath('following::table[count(preceding::h3[regexp:test(., "\d+\.")])={i} and .//font[regexp:test(., "^\d+,\d?$")] and not(.//font[regexp:test(., "\d+/\d+")])]//tr[.//font[regexp:test(., "^\d+,\d?$")]]'.format(i=i))
        for grade in grades:
            grade_name, grade_val = grade.xpath('.//font/text()').strings()
            grade_val = float(grade_val.replace(',', '.'))
            review.grades.append(Grade(name=grade_name, value=grade_val, best=10.0))

        grade_overall = rev.xpath('following::table[count(preceding::h3[regexp:test(., "\d+\.")])={i} and .//font[regexp:test(., "\d+ ?%")] and not(.//font[regexp:test(., "\d+/\d+")])]//font[regexp:test(., "\d+ ?%")]/text()'.format(i=i)).string()
        if grade_overall:
            grade_overall = grade_overall.replace('%', '')
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

        pros = rev.xpath('following::p[count(preceding::h3[regexp:test(., "\d+\.")])={i} and contains(., "Plusy")]/following-sibling::ul[1]/li'.format(i=i))
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            review.add_property(type='pros', value=pro)

        cons = rev.xpath('following::p[count(preceding::h3[regexp:test(., "\d+\.")])={i} and contains(., "Mínusy")]/following-sibling::ul[1]/li'.format(i=i))
        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            review.add_property(type='cons', value=con)

        summary = data.xpath('//div[@class="article__perex"]/p//text()').string(multiple=True)
        if summary:
            review.add_property(type='summary', value=summary)

        excerpt = rev.xpath('following-sibling::p[count(preceding::h3[regexp:test(., "\d+\.")])={i} and not(contains(., "Specifikace") or contains(., "Plusy") or contains(., "Mínusy") or contains(., "Cena") or contains(., "Zdroj") or contains(., "technické parametry") or .//img)]//text()'.format(i=i)).string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
