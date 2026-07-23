from agent import *
from models.products import *


XBRAND = ['Home']


def run(context, session):
    session.queue(Request('https://vacuum-cleaner-advisor.com/', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    brands = data.xpath('//div[contains(div/h2, "Reviews by brand")]/div/ul/li/a')
    for brand in brands:
        name = brand.xpath('text()').string()
        url = brand.xpath('@href').string()

        if brand not in XBRAND:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(brand=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if ' vs ' not in title:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[contains(text(), "Next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review: ', '').replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '').replace('-review', '').replace('-Review', '')
    product.category = 'Vacuum Cleaner'
    product.manufacturer = context['brand']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author_name = 'Nigel Russco'
    review.authors.append(Person(name=author_name, ssid=author_name))

    grade_overall = data.xpath('//p[contains(text(), "rating =")]/span/b//text()').string()
    if grade_overall:
        grade_overall = grade_overall.split('/')[0]
        if grade_overall and grade_overall.isdigit() and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//tbody[contains(., "# Ratings")]/tr[not(contains(., "# Ratings"))]')
    for grade in grades:
        grade_name = grade.xpath('td[1]/text()').string()
        grade_val = grade.xpath('td[2]/text()').string()
        if grade_val:
            grade_val = grade_val.split()[0]
            if grade_name and grade_val and grade_val[0].isdigit() and float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('//td[contains(img/@alt, "Green Check Mark")]')
    for pro in pros:
        pro = pro.xpath('(following-sibling::*)[1][not(@align)]/text()').string()
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//div[contains(text(), "PROS")]/text()[starts-with(normalize-space(.), "-")]')
        if not pros:
            pros = data.xpath('//p[contains(strong/text(), "PROS")]/text()[starts-with(normalize-space(.), "-")]')

        for pro in pros:
            pro = pro.string()
            if pro:
                pro = pro.strip(' +-*.:;•,–')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

    cons = data.xpath('//td[contains(img/@alt, "Red Cross")]')
    for con in cons:
        con = con.xpath('(following-sibling::*)[1][not(@align)]/text()').string()
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//div[contains(text(), "CONS")]/text()[starts-with(normalize-space(.), "-")]')
        if not cons:
            cons = data.xpath('//p[contains(strong/text(), "CONS")]/text()[starts-with(normalize-space(.), "-")]')

        for con in cons:
            con = con.xpath('(following-sibling::*)[1][not(@align)]/text()').string()
            if con:
                con = con.strip(' +-*.:;•,–')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

    summary = data.xpath('//p[contains(text(), "rating =")]//text()[not(contains(., "rating =") or ancestor::span[@color="#009900"])]').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//p[contains(strong, "VERDICT")]|//p[contains(strong, "VERDICT")]/following-sibling::p)[not(preceding-sibling::p[contains(strong, "WARRANTY") or contains(strong, "MANUAL")] or contains(strong, "WARRANTY") or contains(strong, "MANUAL") or contains(strong, "VERDICT") or contains(., "Check the "))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//p[contains(strong, "Verdict")]|//p[contains(strong, "Verdict")]/following-sibling::p)[not(preceding-sibling::p[contains(strong, "Warranty") or contains(strong, "MANUAL")] or contains(strong, "Warranty") or contains(strong, "MANUAL") or contains(strong, "Verdict") or contains(., "Check the "))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//p[contains(strong, "VERDICT")]|//p[contains(strong, "VERDICT")]/following-sibling::p)[not(preceding-sibling::p[contains(strong, "MANUAL")] or contains(strong, "MANUAL") or contains(strong, "VERDICT") or contains(., "Check the "))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//p[contains(strong, "Verdict")]|//p[contains(strong, "Verdict")]/following-sibling::p)[not(preceding-sibling::p[contains(strong, "Manual")] or contains(strong, "Manual") or contains(., "Check the "))]//text()[not(contains(., "Verdict"))]').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[contains(strong, "VERDICT")]/preceding-sibling::p[not(contains(em, "Disclosure:") or @align)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[article]/div/p[not(contains(em, "Disclosure:") or contains(text(), "rating =") or @align or preceding::p[contains(strong, "WARRANTY") or contains(strong, "Warranty") or contains(strong, "MANUAL") or contains(strong, "Verdict") or contains(strong, "Manual")] or contains(strong, "WARRANTY") or contains(strong, "MANUAL") or contains(strong, "VERDICT") or contains(strong, "Verdict") or contains(., "Check the ") or contains(strong, "PROS") or contains(strong, "CONS"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[article]/div/p[not(contains(em, "Disclosure:") or contains(text(), "rating =") or preceding::p[contains(strong, "WARRANTY") or contains(strong, "Warranty") or contains(strong, "MANUAL") or contains(strong, "Verdict") or contains(strong, "Manual")] or contains(strong, "WARRANTY") or contains(strong, "MANUAL") or contains(strong, "VERDICT") or contains(strong, "Verdict") or contains(., "Check the ") or contains(strong, "PROS") or contains(strong, "CONS"))][@align="left"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[article]/div[not(@class)]/div[not(@class or table or contains(text(), "PROS") or contains(text(), "CONS"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
