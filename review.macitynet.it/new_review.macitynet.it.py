from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.macitynet.it/category/recensioni/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('La recensione del ', '').replace('La recensione di ', '').replace('Recensione ', '').replace('Recensione:', '').split(', ')[0].split(' la recensione d')[0].split(': recensione del ')[0].split(': la recensione')[0].replace('Mini recensione ', '').replace('Test: ', '').strip(' +-:.;').capitalize()
    product.ssid = context['url'].split('/')[-2].replace('recensione-', '')

    product.url = data.xpath('//a[contains(@href, ".amazon.") or contains(text(), "Amazon")]/@hre').string()
    if not product.url:
        product.url = context['url']

    category = data.xpath('//a[contains(@class, "entry-category") and not(contains(., "Recensioni"))]/text()').string()
    if category:
        product.category = category.replace(' / ', '|')
    else:
        product.category = 'Tecnologia'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "author")]/text()').string()
    author_url = data.xpath('//a[contains(@class, "author")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "final-score")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//tr[contains(@class, "row-stars")]')
    for grade in grades:
        grade_name = grade.xpath('td[contains(@class, "review-desc")]/text()').string()
        grade_val = grade.xpath('count(.//i[@class="td-icon-star"]) + count(.//i[@class="td-icon-star-half"]) div 2')
        if grade_name and grade_val > 0:
            review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    pros = data.xpath('(//h2|//h3)[.//span[@id="Pro" or normalize-space(text())="Pro"]]/following-sibling::ul[1]/li/text()')
    if not pros:
        pros = data.xpath('(//h2|//h3)[.//span[@id="Pro" or normalize-space(text())="Pro"]]/following-sibling::p[(preceding-sibling::h2[1]|preceding-sibling::h3[1])[.//span[@id="Pro" or normalize-space(text())="Pro"]]]/text()')
    if not pros:
        pros = data.xpath('//p[strong[normalize-space(text())="Pro" or normalize-space(text())="PRO"]]/following-sibling::*[1]/li/text()')
    if not pros:
        pros = data.xpath('//p[strong[normalize-space(text())="Pro" or normalize-space(text())="PRO"]]/following-sibling::*[1]/text()')

    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h2|//h3)[.//span[@id="Contro" or normalize-space(text())="Contro"]]/following-sibling::ul[1]/li/text()')
    if not cons:
        cons = data.xpath('(//h2|//h3)[.//span[@id="Contro" or normalize-space(text())="Contro"]]/following-sibling::p[(preceding-sibling::h2[1]|preceding-sibling::h3[1])[.//span[@id="Contro" or normalize-space(text())="Contro"]]]/text()')
    if not cons:
        cons = data.xpath('//p[strong[normalize-space(text())="Contro" or normalize-space(text())="CONTRO"]]/following-sibling::*[1]/li/text()')
    if not cons:
        cons = data.xpath('//p[strong[normalize-space(text())="Contro" or normalize-space(text())="CONTRO"]]/following-sibling::*[1]/text()')

    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[regexp:test(., "Conclusioni|Conclusione")]/following-sibling::p[not(.//@class="external" or strong[regexp:test(., "Pro|Contro|PRO|CONTRO")] or contains(., "•"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[regexp:test(., "Conclusioni|Conclusione")]]/following-sibling::p[not(.//@class="external" or strong[regexp:test(., "Pro|Contro|PRO|CONTRO")] or contains(., "•"))]//text()').string(multiple=True)

    if conclusion:
        conclusion = re.sub(r'<span[\w\d\s\”\=\_\-\:\’\/\;]+”>|\</span\>','', conclusion.replace(u'\uFEFF', '')).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Conclusioni|Conclusione")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[strong[regexp:test(., "Conclusioni|Conclusione")]]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div/p[not(.//@class="external" or strong[regexp:test(., "Pro|Contro|PRO|CONTRO")] or contains(., "•"))]//text()').string(multiple=True)

    if excerpt:
        excerpt = re.sub(r'<span[\w\d\s\”\=\_\-\:\’\/\;]+”>|\</span\>', '', excerpt.replace(u'\uFEFF', '')).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
