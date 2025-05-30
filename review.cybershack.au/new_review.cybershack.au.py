from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://cybershack.com.au/category/reviews/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if not next_url:
        next_url = data.xpath('//a[contains(@class, "next")]/@href').string()

    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = re.sub(r'\(.+\)', '', context['title'].split(' –  ')[0].split('–')[0].replace('Australian Review: ', '').replace('Game Review: ', '').replace('Film Review: ', '').replace('Australia Review: ', '').replace('Review: ', '')).strip()
    product.ssid = context['url'].split('/')[-2]

    product.url = data.xpath('//a[contains(@href, "www.amazon.com.") or contains(text(), "Amazon")]/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = data.xpath('//div[contains(@class, "post__category")]/a[not(regexp:test(., "Review|Other|Cybershack"))]/text()').join('|')
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if not date:
        date = data.xpath('//div[contains(@class, "post__date")]/text()').string()

    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@href, "https://cybershack.com.au/author/")]/text()').string()
    author_url = data.xpath('//a[contains(@href, "https://cybershack.com.au/author/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "final-score")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    if not grade_overall:
        overall = data.xpath('//h3[regexp:test(text(), " rating", "i")]/following-sibling::p[not(preceding-sibling::p[strong[contains(text(), "Pro") or contains(text(), "Con")]] or strong[contains(text(), "Pro")])]//text()').string(multiple=True)
        if overall:
            grade_overall = re.search(r'\d+\.?\d?/5|\d+\.?/10|\d+\.?\d?/20|\d+\.?\d?/100', overall)
            if grade_overall:
                grade_overall, grade_best = grade_overall.group(0).split('/')
                if float(grade_best) >= float(grade_overall):
                    review.grades.append(Grade(type='overall', value=float(grade_overall), best=float(grade_best)))

    grades = data.xpath('//div[contains(@class, "score-title")]')
    for grade in grades:
        grade_name = grade.xpath('div[contains(@class, "text")]/text()').string()
        grade_val = grade.xpath('.//div[contains(@class, "code")]/text()').string()
        if grade_name and grade_val:
            grade_val = grade_val.split('/')[0]
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pro = data.xpath('//p[strong[contains(., "Pro")]]/text()[preceding-sibling::strong[1][contains(., "Pro")] and not(regexp:test(normalize-space(.), "^Pro|^Con"))]').string()
    if pro:
        review.add_property(type='pros', value=pro)

    if not pro:
        pros = data.xpath('//div[h3[normalize-space(text())="Pros"]]/div[contains(@class, "review__list")]//span[contains(@class, "item-text")]')
        if not pros:
            pros = data.xpath('//p[strong[contains(., "Pro")]]/following-sibling::ul[1]/li')
        if not pros:
            pros = data.xpath('//p[strong[contains(., "Pro")]]/following-sibling::p[preceding-sibling::p[strong][1][strong[contains(., "Pro")]]][not(strong)]')

        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            if pro:
                pro = pro.replace('\uFEFF', '').strip(' +-*.;•–')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

    con = data.xpath('//p[strong[contains(., "Con")]]/text()[preceding-sibling::strong[1][contains(., "Con")] and not(regexp:test(normalize-space(.), "^Pro|^Con"))]').string()
    if con:
        review.add_property(type='cons', value=con)

    if not con:
        cons = data.xpath('//div[h3[normalize-space(text())="Cons"]]/div[contains(@class, "review__list")]//span[contains(@class, "item-text")]')
        if not cons:
            cons = data.xpath('//p[strong[contains(., "Con")]]/following-sibling::ul[1]/li')
        if not cons:
            cons = data.xpath('//p[strong[contains(., "Con")]]/following-sibling::p[preceding-sibling::p[strong][1][strong[contains(., "Con")]]][not(strong or @class or normalize-space(text())="None")]')

        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            if con:
                con = con.replace('\uFEFF', '').strip(' +-*.;•–')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h4[contains(., "Would I buy it?")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[regexp:test(text(), " rating", "i")]/following-sibling::p[not(preceding-sibling::p[strong[contains(text(), "Pro") or contains(text(), "Con")]] or strong[contains(text(), "Pro")])]//text()').string(multiple=True)

    if conclusion:
        conclusion = re.sub(r'\d+\.?\d?/5|\d+\.?/10|\d+\.?\d?/20|\d+\.?\d?/100', '', conclusion).replace('\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h4[contains(., "Would I buy it?")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h3[regexp:test(text(), " rating", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content")]/p[not(@class or preceding-sibling::p[strong[contains(text(), "Pro") or contains(text(), "Con")]] or strong[contains(text(), "Pro")])]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace('\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
