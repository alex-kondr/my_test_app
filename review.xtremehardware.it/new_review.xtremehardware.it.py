from agent import *
from models.products import *
import re
import HTMLParser


h = HTMLParser.HTMLParser()
XCAT = ['English Articles']


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(h.unescape(line) + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.xtremehardware.com/', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[a[contains(., "Recensioni")]]/ul/li/a')
    for cat in cats:
        name = cat.xpath('preceding-sibling::strong[1]/text()').string()
        subcat_name = cat.xpath('text()').string()

        if subcat_name not in XCAT:
            url = cat.xpath('@href').string()
            session.queue(Request(url, force_charset='utf-8'), process_revlist, dict(cat=name + '|' + subcat_name))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//a[@class="grid-card"]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(context, url=url))

    next_url = data.xpath('//a[@class="page-btn" and contains(., "›")]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    title = data.xpath('//h1[@class="article-title"]//text()').string(multiple=True)
    if not title:
        return

    product = Product()
    product.name = title.replace('Preview: ', '').replace('Recensione: ', '').split(': ')[0].replace(' - Recensione', '').replace('Recensione ', '').replace(', La Recensione', '').replace(' La Recensione', '').replace(', la nostra recensione', '').replace(', la recensione', '').replace('[Preview] ', '').replace(' – Recensione', '').replace('Videorecensione ', '').replace(' - La recensione!', '').split(', preview del')[0].replace(' Beta Testing', '').replace(', recensione/review', '').replace(', la videorecensione', '').replace('[VideoRecensione] ', '').replace('Review ', '').replace(', LA RECENSIONE', '').split(' Review, ')[0].replace(' - la recensione!', '').replace(' - La recensione', '').replace('La videorecensione di ', '').replace(' - RECENSIONE', '').replace(' recensione', '').strip()
    product.ssid = context['url'].split('/')[-1].split('-')[0]
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[contains(span, "Brand")]/span[@class="product-value"]/text()').string()

    product.url = data.xpath('//a[contains(., "Vedi Offerta")]/@href').string()
    if not product.url:
        product.url = context['url']

    mpn = data.xpath('//div[contains(span, "Modello")]/span[@class="product-value"]/text()').string()
    if mpn and mpn.replace(' ', '').isupper():
        product.add_property(type='id.manufacturer', value=mpn)

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//span[@class="article-date"]/text()').string()

    author = data.xpath('//div[@class="article-byline"]/span/strong/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//tr[contains(., "Complessivo") and not(preceding::div[@class="related-section"])]//img/@alt[regexp:test(., "\d+")]').string()
    if grade_overall:
        grade_overall = grade_overall.split()[0].replace(',', '.')
        try:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))
        except:
            pass

    if not grade_overall:
        grade_overall = data.xpath('//span[@class="rating-score"]/text()').string()
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//h1[contains(., "Conclusioni")]/following-sibling::table//tr[not(contains(., "Complessivo"))]')
    if not grades:
        grades = data.xpath('//p[.//strong[contains(., "Conclusioni")]]/following-sibling::table//tr[not(contains(., "Complessivo"))]')

    for grade in grades:
        grade_name = grade.xpath('.//strong/text()').string() or grade.xpath('td/b/text()').string()
        grade_desc = grade.xpath('.//p[not(strong or img)]/text()').string(multiple=True) or grade.xpath('td/text()').string()
        grade_val = grade.xpath('(.//img/@alt|.//img/@src)[regexp:test(., "\d+")]').string()
        if grade_val:
            grade_val = re.search(r'\d+[,\.]?\d?', grade_val).group().replace(',', '.')
            if grade_desc and grade_name:
                review.grades.append(Grade(name=grade_name.strip(' :'), value=float(grade_val), best=5.0, description=grade_desc))
            else:
                if not grade_name:
                    grade_name = grade.xpath('td//text()').string(multiple=True)

                if grade_name:
                    review.grades.append(Grade(name=grade_name.strip(' :'), value=float(grade_val), best=5.0))

    pros = data.xpath('(//h4[contains(text(), "Pro")]/following-sibling::*)[1]/li')
    if not pros:
        pros = data.xpath('(//p[strong[contains(text(), "Pro")]]/following-sibling::*)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h4[contains(text(), "Contro")]/following-sibling::*)[1]/li')
    if not cons:
        cons = data.xpath('(//p[strong[contains(text(), "Contro")]]/following-sibling::*)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//section[contains(@class, "article-content")]/p[@align="center"]//text()').string()
    if not summary:
        summary = data.xpath('//p[@class="article-excerpt"]//text()').string(multiple=True)

    if summary:
        summary = summary.replace(u'\uFEFF', '').replace('[...]', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h1[regexp:test(., "Conclusioni", "i")]/following-sibling::p[not(strong/text()[normalize-space(.)]="Pro" or strong/text()[normalize-space(.)]="Contro" or preceding-sibling::p[strong/text()[normalize-space(.)]="Pro" or strong/text()[normalize-space(.)]="Contro"])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[.//strong[contains(., "Conclusioni")]]/following-sibling::p[not(strong[regexp:test(text(), "Pro|Contro")] or @align)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[contains(., "Verdetto") or contains(., "Finale")]/following-sibling::p//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').replace('[...]', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h1[regexp:test(., "Conclusioni", "i")]/preceding-sibling::p[not(@align)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[.//strong[contains(., "Conclusioni")]]/preceding-sibling::p[not(@align)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//section[contains(@class, "article-content")]/p[not(strong[regexp:test(text(), "Pro|Contro")] or @align)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="article-content"]/p[not(strong/text()[normalize-space(.)]="Pro" or strong/text()[normalize-space(.)]="Contro" or preceding-sibling::p[strong/text()[normalize-space(.)]="Pro" or strong/text()[normalize-space(.)]="Contro"])]//text()').string(multiple=True)

    last_page = data.xpath('//a[contains(@class, "page-btn") and not(contains(@class, "active"))]').last()
    if last_page:
        pages_cnt = int(last_page.xpath('text()').string())
        for i in range(1, pages_cnt+1):
            title = review.title + ' - Pagina ' + str(i)
            page_url = data.response_url + '?page=' + str(i)
            review.add_property(type='pages', value=dict(title=title, url=page_url))

        session.do(Request(page_url, force_charset='utf-8'), process_review_last, dict(product=product, review=review, excerpt=excerpt, grade_overall=grade_overall, is_last_page=True))

    elif excerpt:
        context['product'] = product
        context['review'] = review
        context['excerpt'] = excerpt

        process_review_last(data, context, session)


def process_review_last(data, context, session):
    strip_namespace(data)

    review = context['review']

    if context.get('is_last_page'):
        grade_overall = context['grade_overall']
        if not grade_overall:
            grade_overall = data.xpath('//tr[contains(., "Complessivo") and not(preceding::div[@class="related-section"])]//img/@alt[regexp:test(., "\d+")]').string()
            if grade_overall:
                grade_overall1 = grade_overall.split()[0].replace(',', '.')
                try:
                    review.grades.append(Grade(type='overall', value=float(grade_overall1), best=5.0))
                except:
                    pass

        if not grade_overall:
            grade_overall = data.xpath('//span[@class="rating-score"]/text()').string()
            if grade_overall and float(grade_overall) > 0:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

        grades = data.xpath('//h1[contains(., "Conclusioni")]/following-sibling::table//tr[not(contains(., "Complessivo"))]')
        if not grades:
            grades = data.xpath('//p[.//strong[contains(., "Conclusioni")]]/following-sibling::table//tr[not(contains(., "Complessivo"))]')

        for grade in grades:
            grade_name = grade.xpath('.//strong/text()').string() or grade.xpath('td/b/text()').string()
            grade_desc = grade.xpath('.//p[not(strong or img)]/text()').string(multiple=True) or grade.xpath('td/text()').string()
            grade_val = grade.xpath('(.//img/@alt|.//img/@src)[regexp:test(., "\d+")]').string()
            if grade_val:
                grade_val = re.search(r'\d+[,\.]?\d?', grade_val).group().replace(',', '.')
                if grade_desc and grade_name:
                    review.grades.append(Grade(name=grade_name.strip(' :'), value=float(grade_val), best=5.0, description=grade_desc))
                else:
                    if not grade_name:
                        grade_name = grade.xpath('td//text()').string(multiple=True)

                    if grade_name:
                        review.grades.append(Grade(name=grade_name.strip(' :'), value=float(grade_val), best=5.0))

        pros = data.xpath('(//h4[contains(text(), "Pro")]/following-sibling::*)[1]/li')
        if not pros:
            pros = data.xpath('(//p[strong[contains(text(), "Pro")]]/following-sibling::*)[1]/li')

        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            if pro:
                pro = pro.strip(' +-*.:;•,–')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

        cons = data.xpath('(//h4[contains(text(), "Contro")]/following-sibling::*)[1]/li')
        if not cons:
            cons = data.xpath('(//p[strong[contains(text(), "Contro")]]/following-sibling::*)[1]/li')

        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            if con:
                con = con.strip(' +-*.:;•,–')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

        conclusion = data.xpath('//h1[regexp:test(., "Conclusioni", "i")]/following-sibling::p[not(strong/text()[normalize-space(.)]="Pro" or strong/text()[normalize-space(.)]="Contro" or preceding-sibling::p[strong/text()[normalize-space(.)]="Pro" or strong/text()[normalize-space(.)]="Contro"])]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//p[.//strong[contains(., "Conclusioni")]]/following-sibling::p[not(strong[regexp:test(text(), "Pro|Contro")] or @align)]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//h3[contains(., "Verdetto") or contains(., "Finale")]/following-sibling::p//text()').string(multiple=True)

        if conclusion:
            conclusion = conclusion.replace(u'\uFEFF', '').replace('[...]', '').strip()
            review.add_property(type='conclusion', value=conclusion)

        excerpt = data.xpath('//h1[regexp:test(., "Conclusioni", "i")]/preceding-sibling::p[not(@align)]//text()').string(multiple=True)
        if not excerpt and not data.xpath('//h1[contains(., "Conclusioni")]'):
            excerpt = data.xpath('//p[.//strong[contains(., "Conclusioni")]]/preceding-sibling::p[not(@align)]//text()').string(multiple=True)
            if not excerpt:
                excerpt = data.xpath('//section[contains(@class, "article-content")]/p[not(strong[regexp:test(text(), "Pro|Contro")] or @align)]//text()').string(multiple=True)
            if not excerpt:
                excerpt = data.xpath('//div[@class="article-content"]/p[not(strong/text()[normalize-space(.)]="Pro" or strong/text()[normalize-space(.)]="Contro" or preceding-sibling::p[strong/text()[normalize-space(.)]="Pro" or strong/text()[normalize-space(.)]="Contro"])]//text()').string(multiple=True)

        if excerpt:
            context['excerpt'] += ' ' + excerpt

    if context['excerpt']:
        excerpt = context['excerpt'].replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
