from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.nirmaltv.com/category/reviews/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


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
    product.name = context['title'].split(' Review- ')[0].split(' Review: ')[-1].replace('Review- ', '').replace('Review – ', '').replace('Review: ', '').replace('Review : ', '').replace(' [Review]', '').replace(' Review', '').replace('Review ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = data.xpath('//a[@rel="tag" and not(regexp:test(., "Review|Sponsored"))]/text()').string() or 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "meta_author")]//text()[not(contains(., "by"))]').string(multiple=True)
    author_url = data.xpath('//div[contains(@class, "meta_author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="score_value"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//div[@data-scoretype="point"]/ul/li')
    for grade in grades:
        grade_name = grade.xpath('strong/text()').string()
        grade_val = grade.xpath('.//span/@data-width').string()
        if grade_name and grade_val and grade_val.isdigit():
            grade_val = float(grade_val) / 10
            review.grades.append(Grade(name=grade_name, value=grade_val, best=10.0))

    pros = data.xpath('//div[h3[contains(., "PROS")]]//li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[h3[contains(., "CONS")]]//li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('(//h3|//h4)[contains(., "Verdict")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[contains(., "Verdict")]]/following-sibling::p//text()').string()

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    summary = data.xpath('//div[@class="desc"]/p//text()').string(multiple=True)
    if summary and conclusion:
        review.add_property(type='summary', value=summary)
    elif summary:
        review.add_property(type='conclusion', value=summary)

    excerpt = data.xpath('(//h3|//h4)[contains(., "Verdict")]/preceding-sibling::p[not(contains(., "Related Reading:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[strong[contains(., "Verdict")]]/preceding-sibling::p[not(contains(., "Related Reading:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content")]/p[not(contains(., "Related Reading:"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
