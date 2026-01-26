from agent import *
from models.products import *


XCAT = ['Tools & DIY', 'About GearLab']
XTITLE = ['best ', 'how to', 'advice']


def run(context, session):
    session.queue(Request('https://www.techgearlab.com', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[contains(@class, "menu-list")]/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        sub_cats = cat.xpath('ul/li/a')
        for sub_cat in sub_cats:
            subcat_name = sub_cat.xpath('text()').string()
            url = sub_cat.xpath('@href').string()

            if url and subcat_name and not subcat_name.startswith("All "):
                session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name+'|'+subcat_name))


def process_revlist(data, context, session):
    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if title and not any(xtitle in title.lower() for xtitle in XTITLE):
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat'].replace('More|', '')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    review.date = data.xpath('//div[contains(text(), "By") and a[contains(@href, "/author/")]]/span/text()').string()
    if not review.date:
        date = data.xpath('//div[contains(text(), "By") and a[contains(@href, "/author/")]]/following-sibling::div[1][@class="small"]/text()').string()
        if date:
            review.date = date.split(' ', 1)[-1]

    author = data.xpath('//div[contains(text(), "By")]/a[contains(@href, "/author/")]/text()').string()
    author_url = data.xpath('//div[contains(text(), "By")]/a[contains(@href, "/author/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "table_score_top")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//li[contains(@class, "rating")]/div[contains(@class, "label")]')
    for grade in grades:
        grade_name = grade.xpath('span//text()').string(multiple=True)
        grade_val = grade.xpath('strong//text()').string(multiple=True)
        if grade_name and grade_val and float(grade_val) > 0:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('//div[@class="iconProText"]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="iconConText"]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="subhead"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::text()|(//h2[contains(., "Conclusion")]/following-sibling::a//h2[contains(., "Conclusion")]/following-sibling::span|//h2[contains(., "Conclusion")]/following-sibling::strong|//h2[contains(., "Conclusion")]/following-sibling::em)//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="summary_larger"]/div[@class="articletext"]//text()[not(preceding::*[contains(., "REASONS TO")] or contains(., "REASONS TO"))]').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[not(@class)]/div[@class="articletext"]/p[not(preceding::h2[contains(., "Conclusion")])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
