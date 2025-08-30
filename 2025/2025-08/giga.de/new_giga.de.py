from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.giga.de/tech/tests/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
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
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_ssid))

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

    if not grades:
        grades = data.xpath('//div[@class="table-responsive"]/table[contains(., "Kategorie")]/tr[not(contains(., "Kategorie"))]')
        if not grades:
            grades = data.xpath('//div[contains(@class, "table__responsive")]/table[contains(., "Kategorie")]/tr[not(contains(., "Kategorie"))]')

        for grade in grades:
            grade_name, grade_val = grade.xpath('.//text()').strings()
            if grade_name and grade_val and grade_val.strip().isdigit():
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath("(//p[contains(.,'Vorteile')]/following-sibling::ul)[1]//li")
    if not pros:
        pros = data.xpath('//li[@class="arg-pro"]')
    if not pros:
        pros = data.xpath('//p[strong[contains(., "Vorteile")]]')
    if not pros:
        pros = data.xpath('//span[strong[contains(., "Vorteile")]]')
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
        pros = data.xpath('//h2[contains(., "Das hat uns gut gefallen")]/following-sibling::ul[1]/li[not(@class)]')

    for pro in pros:
        pro_ = pro.xpath('.//text()[contains(., "+")]').strings()
        for _pro in pro_:
            _pro = _pro.replace('+', '').strip()
            review.add_property(type='pros', value=_pro)
        if not pro_:
            pro_ = pro.xpath('.//text()').string(multiple=True)
            if pro:
                pro_ = pro_.replace('+', '').strip()
                review.add_property(type='pros', value=pro_)

    cons = data.xpath("(//p[contains(.,'Nachteile')]/following-sibling::ul)[1]//li")
    if not cons:
        cons = data.xpath('//li[@class="arg-con"]')
    if not cons:
        cons = data.xpath('//p[strong[contains(., "Nachteile")]]')
    if not cons:
        cons = data.xpath('//span[strong[contains(., "Nachteile")]]')
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
        cons = data.xpath('//h2[contains(., "nicht so gut")]/following::ul[1]/li[not(@class)]')

    if pros:
        for con in cons:
            con_ = con.xpath('.//text()[contains(., "-")]').strings()
            for _con in con_:
                _con = _con.replace('-', '').strip()
                review.add_property(type='cons', value=_con)
            if not con_:
                con_ = con.xpath('.//text()').string(multiple=True)
                if con_:
                    con_ = con_.replace('-', '').strip()
                    review.add_property(type='cons', value=con_)

    summary = data.xpath('//div[@data-init="toc-box"]/preceding-sibling::p//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//div[@data-init="product-box"]/preceding-sibling::p//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//div[@class="product-box-content"]/following-sibling::p[1]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//div[contains(@class, "alice-layout-article-body")]/p[1]//text()').string(multiple=True)

    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Persönliches Fazit:")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Spezifikationen") or contains(., "Facebook") or contains(., "Twitter") or figure or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Fazit")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Facebook") or contains(., "Twitter") or figure or contains(., "wertung") or contains(., "US-Dollar") or contains(., "nicht gefallen") or contains(., "Wertung:") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Fazit zur")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Facebook") or contains(., "Twitter") or figure or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Testfazit")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Facebook") or contains(., "Twitter") or contains(., "Preis") or contains(., "Links") or contains(., "für die Unterstützung!") or figure or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="topic"]/p[not(contains(., "Wertung:") or contains(., "Pro:") or contains(., "Contra:") or contains(., "Gut zu wissen:") or contains(., "Vorteile:") or contains(., "Nachteile:") or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//p[contains(., "Fazit:")]|//p[contains(., "Fazit:")]/following-sibling::p[not(contains(., "Facebook") or contains(., "Twitter") or contains(., "Disclosure:") or (contains(., "Gesamt") or .//strong[contains(., "Alles Weitere dazu")]) or @class="taboola-text")])//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="update"]/p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p/strong[contains(., "Mein persönliches Fazit")]/parent::p//text()').string(multiple=True)

    excerpt = data.xpath('//h3[contains(., "Persönliches Fazit:")]/preceding-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or figure or @class="taboola-text")]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Fazit")]/preceding-sibling::p[not(contains(., "Euro UVP") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Fazit zur")]/preceding-sibling::p[not(contains(., "Euro UVP") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Testfazit")]/preceding-sibling::p[not(contains(., "Euro UVP") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@data-init="toc-box"]/following-sibling::p[not(contains(., "Facebook") or contains(., "Twitter") or em or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(., "Fazit:")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="topic"]/following-sibling::p[not(contains(., "Facebook") or contains(., "Twitter") or em or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="update"]/following-sibling::p[not(@class|figure|em or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[@class="p1"][not(contains(., "Nächste Seite:") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body//p[not(figure or @class or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "alice-layout-article-body")]/p[not(figure or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter") or contains(., "Auf Seite") or contains(., "Vorteile:") or contains(., "Nachteile:") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)

    if excerpt and summary:
        excerpt = excerpt.replace(summary, '').strip()

    context['product'] = product
    context['conclusion'] = conclusion
    context['excerpt'] = excerpt

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        review.add_property(type='pages', value=dict(title=review.title + ' - page 1', url=context['url']))
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_review_next, dict(context, review=review, url=next_url, page=2))
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

        if not grades:
            grades = data.xpath('//div[@class="table-responsive"]/table[contains(., "Kategorie")]/tr[not(contains(., "Kategorie"))]')
            if not grades:
                grades = data.xpath('//div[contains(@class, "table__responsive")]/table[contains(., "Kategorie")]/tr[not(contains(., "Kategorie"))]')

            for grade in grades:
                grade_name, grade_val = grade.xpath('.//text()').strings()
                if grade_name and grade_val:
                    review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

        pros = data.xpath("(//p[contains(.,'Vorteile')]/following-sibling::ul)[1]//li")
        if not pros:
            pros = data.xpath('//li[@class="arg-pro"]')
        if not pros:
            pros = data.xpath('//p[strong[contains(., "Vorteile")]]')
        if not pros:
            pros = data.xpath('//span[strong[contains(., "Vorteile")]]')
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
            pros = data.xpath('//h2[contains(., "Das hat uns gut gefallen")]/following-sibling::ul[1]/li[not(@class)]')

        for pro in pros:
            pro_ = pro.xpath('.//text()[contains(., "+")]').strings()
            for _pro in pro_:
                _pro = _pro.replace('+', '').strip()
                review.add_property(type='pros', value=_pro)
            if not pro_:
                pro_ = pro.xpath('.//text()').string(multiple=True)
                if pro_:
                    pro_ = pro_.replace('+', '').strip()
                review.add_property(type='pros', value=pro_)

        cons = data.xpath('(//p[strong[contains(., "Nachteile")]]/following-sibling::ul)[1]//li')
        if not cons:
            cons = data.xpath('//li[@class="arg-con"]')
        if not cons:
            cons = data.xpath('//p[strong[contains(., "Nachteile")]]')
        if not cons:
            cons = data.xpath('//span[strong[contains(., "Nachteile")]]')
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
            cons = data.xpath('//h2[contains(., "nicht so gut")]/following::ul[1]/li[not(@class)]')

        for con in cons:
            con_ = con.xpath('.//text()[contains(., "-")]').strings()
            for _con in con_:
                _con = _con.replace('-', '').strip()
                review.add_property(type='cons', value=_con)
            if not con_:
                con_ = con.xpath('.//text()').string(multiple=True)
                if con_:
                    con_ = con_.replace('-', '').strip()
                review.add_property(type='cons', value=con_)

        if not conclusion:
            conclusion = data.xpath('//h3[contains(., "Persönliches Fazit:")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Spezifikationen") or contains(., "Facebook") or contains(., "Twitter") or figure or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//h2[contains(., "Fazit")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Facebook") or contains(., "Twitter") or figure or contains(., "wertung") or contains(., "US-Dollar") or contains(., "nicht gefallen") or contains(., "Wertung:") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//h2[contains(., "Fazit zur")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Facebook") or contains(., "Twitter") or figure or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//h2[contains(., "Testfazit")]/following-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or contains(., "Facebook") or contains(., "Twitter") or contains(., "Preis") or contains(., "Links") or contains(., "für die Unterstützung!") or figure or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//div[@class="topic"]/p[not(contains(., "Wertung:") or contains(., "Pro:") or contains(., "Contra:") or contains(., "Gut zu wissen:") or contains(., "Vorteile:") or contains(., "Nachteile:") or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('(//p[contains(., "Fazit:")]|//p[contains(., "Fazit:")]/following-sibling::p[not(contains(., "Facebook") or contains(., "Twitter") or contains(., "Disclosure:") or (contains(., "Gesamt") or .//strong[contains(., "Alles Weitere dazu")]) or @class="taboola-text")])//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//div[@class="update"]/p//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//p/strong[contains(., "Mein persönliches Fazit")]/parent::p//text()').string(multiple=True)

        excerpt = data.xpath('//h3[contains(., "Persönliches Fazit:")]/preceding-sibling::p[not(contains(., "Vorteile") or contains(., "Nachteile") or contains(., "Gesamt:") or contains(., "Einzelwertung") or figure or @class="taboola-text")]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//h2[contains(., "Fazit")]/preceding-sibling::p[not(contains(., "Euro UVP") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//h2[contains(., "Fazit zur")]/preceding-sibling::p[not(contains(., "Euro UVP") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//h2[contains(., "Testfazit")]/preceding-sibling::p[not(contains(., "Euro UVP") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[@data-init="toc-box"]/following-sibling::p[not(contains(., "Facebook") or contains(., "Twitter") or em or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//p[contains(., "Fazit:")]/preceding-sibling::p//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[@class="topic"]/following-sibling::p[not(contains(., "Facebook") or contains(., "Twitter") or em or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[@class="update"]/following-sibling::p[not(@class|figure|em or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//p[@class="p1"][not(contains(., "Nächste Seite:") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//body//p[not(figure or @class or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[contains(@class, "alice-layout-article-body")]/p[not(figure or contains(., "Gesamt") or contains(., "Facebook") or contains(., "Twitter") or contains(., "Auf Seite") or contains(., "Vorteile:") or contains(., "Nachteile:") or .//strong[contains(., "Alles Weitere dazu")] or @class="taboola-text")]//text()').string(multiple=True)

        if excerpt and len(excerpt) > 10:
            context['excerpt'] += ' ' + excerpt

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_review_next, dict(context, review=review, conclusion=conclusion, url=next_url, page=page + 1))

    elif context['excerpt'] and len(context['excerpt']) > 10:
        product = context['product']

        if conclusion:
            conclusion = conclusion.replace('Fazit:', '').replace('Kurz-Fazit vorweg:', '').strip()
            review.add_property(type='conclusion', value=conclusion)

            context['excerpt'] = context['excerpt'].replace(conclusion, '').strip()


        review.add_property(type="excerpt", value=context['excerpt'])

        product.reviews.append(review)

        session.emit(product)
