from agent import *
from models.products import *
import re
import time
import random


XCAT = ['News & Announcements', 'News']


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request('https://www.theaterbyte.com/', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform( 1, 3))

    cats = data.xpath('//ul[contains(@class, "menu-items")]/li')
    for cat in cats:
        name = cat.xpath('div/text()').string()

        sub_cats = cat.xpath('ul[@class="sub-menu"]/li')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('div/text()').string().replace(name, '').strip()
            url = sub_cat.xpath('a/@href').string()

            if sub_name not in XCAT:
                session.queue(Request(url, force_charset='utf-8'), process_revlist, dict(cat=name + '|' + sub_name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform( 1, 3))

    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform( 1, 3))

    product = Product()
    product.name = re.compile(r'Preview.?:|Review.?:|\[.+\]|Preview |Review |Blind Test.?:| Review|\(.+\)|Baka & Test:', flags=re.I).sub('', context['title'].split('Review –')[0].split(' – ')[0]).strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = context['cat']

    product.url = data.xpath('//a[regexp:test(@href, "https://www.hulu.com/movie|https://amzn.to/")]/@href').string()
    if not product.url:
        product.url = context['url']

    manufacturer = data.xpath('//li[regexp:test(., "Studios|Distributors")]/text()').string()
    if manufacturer:
        product.manufacturer = manufacturer.split(':')[-1].split('|')[0].strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('(//a[contains(@class, "author-name")]|//div[contains(@class, "author-name")]/a)//text()').string()
    author_url = data.xpath('(//a[contains(@class, "author-name")]|//div[contains(@class, "author-name")]/a)/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//text()[contains(., "[Rating:") and preceding-sibling::text()[1][contains(., "Overall")]]').string()
    if grade_overall:
        grade_overall = grade_overall.split(':')[-1].split('/')[0].strip()
        if grade_overall and grade_overall[0].isdigit() and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//tr[@class="td-review-row-stars"]')
    for grade in grades:
        grade_name = grade.xpath('td[@class="td-review-desc"]/text()').string()
        grade_val = grade.xpath('count(.//i[@class="td-icon-star"]) + count(.//i[@class="td-icon-star-half"]) div 2')
        review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    if not grades:
        grades = data.xpath('(//p[.//strong[contains(text(), "[Rating:")]])[1]//text()[not(contains(., "Scorecard:"))][normalize-space(.)]').strings()
        if len(grades) > 1:
            for i, grade in enumerate(grades, start=1):
                if i % 2 == 0:
                    grade_val = grade.split(':')[-1].split('/')[0].strip()
                    try:
                        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))
                    except:
                        pass
                else:
                    grade_name = grade.strip()

    if not grades:
        grades = data.xpath('(//strong[contains(., "[Rating:")])[1]//text()[contains(., "[Rating:") and not(preceding-sibling::text()[1][contains(., "Overall")])]')

        for grade in grades:
            grade_name = grade.xpath('preceding-sibling::text()').string()
            grade_val = grade.string().split(':')[-1].split('/')[0].strip()
            try:
                if grade_name and grade_val and grade_val[0].isdigit() and float(grade_val) > 0:
                    grade_name = grade_name.strip(' :')
                    review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))
            except:
                pass

    pros = data.xpath('(//h2[contains(., "Pros:")]/following-sibling::*)[1]/li')
    if not pros:
        pros = data.xpath('(//p[.//strong[contains(text(), "The Good:")]]/following-sibling::*)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h2[contains(., "Cons:")]/following-sibling::*)[1]/li')
    if not cons:
        cons = data.xpath('(//p[.//strong[contains(text(), "The Bad:")]]/following-sibling::*)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "summary-content")]//text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(@class, "final|verdict") or regexp:test(., "Final|Verdict")]/following-sibling::p[not(contains(@class, "block") or (.//a[contains(@href, "amzn.to")] and contains(., "Purchase")))]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(@class, "final|verdict") or regexp:test(., "Final|Verdict")][1]/preceding-sibling::p[not(contains(@class, "block") or (.//a[contains(@href, "amzn.to")] and contains(., "Purchase")))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "block-inner")]/p[not(contains(@class, "block") or @style or regexp:test(., "\[amazon|BestBuy.com:|Shop for more|Amazon.com|Rating:", "i") or (regexp:test(., "\w:") and string-length(.)<20) or (.//a[contains(@href, "amzn.to")] and contains(., "Purchase")))]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
