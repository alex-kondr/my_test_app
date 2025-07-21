from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://silentpcreview.com/?s=review', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3/a')

    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if title and not re.search(r'Save \d+%|^(The )?Best | deal', title, flags=re.I):
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-preview', '').replace('-review', '')
    product.manufacturer = data.xpath('//tr[contains(., "Manufacturer")]//b[not(contains(., "Manufacturer"))]/text()').string()

    product.name = data.xpath('//tr[contains(., "Product")]//b[not(contains(., "Product"))]/text()').string()
    if not product.name:
        product.name = context['title'].split(' – ')[0].split(' Preview :')[0].split(' Preview:')[0].split(' Preview -')[0].split(' Preview –')[0].split(' Review:')[0].split(' Reviewed ')[0].replace('Preview ', '').replace('Review ', '').replace('Reviewed ', '').strip()

    product.category = data.xpath('//p[@id="breadcrumbs"]//a[not(regexp:test(., "Home|Uncategorized"))]/text()').string()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content|//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//li[@itemprop="author"]//span[contains(@class, "author")]/text()').string(multiple=True)
    author_url = data.xpath('//li[@itemprop="author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//strong[regexp:test(text(), "^\d/\d") and not(regexp:test(., "date|MB/s"))]/text()').string(multiple=True)
    if not grade_overall:
        grade_overall = data.xpath('//h5[contains(@class, "rating")]/span[not(contains(., "/"))]/text()').string()

    if grade_overall:
        grade_overall = float(grade_overall.split('/')[0])
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    grades = False
    grade_names = data.xpath('//table[.//td[regexp:test(text(), "\d/\d")]]//th')
    grade_vals = data.xpath('//table[.//td[regexp:test(text(), "\d/\d")]]//td')
    if len(grade_names) == len(grade_vals):
        for grade_name, grade_val in zip(grade_names, grade_vals):
            grade_name = grade_name.xpath('.//text()').string(multiple=True)
            grade_val = grade_val.xpath('.//text()').string(multiple=True)
            if grade_val and grade_name:
                grades = True
                grade_val = float(grade_val.split('/')[0])
                review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    pros = data.xpath('//div[@class="pros"]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="cons"]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[span[contains(@id, "more-")]]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//div[@class="elementor-text-editor elementor-clearfix" and not(p)]//text()').string(multiple=True)

    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[contains(., "FINAL THOUGHTS")]/following-sibling::p[not(@align)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[regexp:test(., "Conclusion|Verdict", "i")]/following-sibling::p[not(@align)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[div[span[contains(text(), "What We Think")]]]/p//text()').string(multiple=True)

    if conclusion:
        conclusion = re.sub(r'^\d/\d', '', conclusion).strip(' :')
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[contains(., "FINAL THOUGHTS")]/preceding-sibling::p[not(@align or @id or span[contains(@id, "more-")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[regexp:test(., "Conclusion|Verdict", "i")]/preceding-sibling::p[not(@align or @id or span[contains(@id, "more-")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//body|//div[@class="elementor-widget-container"])/p[not(@align or @id or span[contains(@id, "more-")])]//text()').string(multiple=True)

    if excerpt and any([grade_overall, grades, pros, cons, conclusion]):
        excerpt = re.sub(r'^\d/\d', '', excerpt).strip(' :')
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
