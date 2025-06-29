from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.digitalcameraworld.com/reviews', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    current_page = data.xpath('//div[@class="flexi-pagination"]//span[@class="active"]/text()').string()
    page = context.get('page', 1)
    if int(current_page) != page:
        return

    revs = data.xpath('//a[@class="article-link"]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(url=url))

    next_page = page + 1
    next_url = 'https://www.digitalcameraworld.com/reviews/page/{}'.format(next_page)
    session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    title = data.xpath('//h1[contains(@class, "title")]//text()').string(multiple=True)
    if not title:
        return

    product = Product()
    product.name = title.split(' review')[0].strip()
    product.ssid = context['url'].split('/')[-1].replace('-review', '')
    product.category = data.xpath('//li[not(@class)]//a[@data-before-rewrite-localise]/text()').string() or 'Tech'

    product.url = data.xpath('//a[@data-product-key and contains(@href, "www.amazon.com")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]//text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="chunk rating"]/@aria-label').string()
    if grade_overall:
        grade_overall = grade_overall.replace('Rating:', '').split(' out ')[0].strip()
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//tr[@class="table__body__row" and contains(., "★")]')
    for grade in grades:
        grade_name = grade.xpath('td[1]/*[not(contains(., "★"))]//text()').string()
        if not grade_name:
            grade_name = grade.xpath('td/*[contains(., "★")]//text()').string().split('★')[0].strip()

        grade_val = grade.xpath('td/*[contains(., "★")]//text()').string().count('★')
        grade_desc = grade.xpath('td[2]/*//text()').string()
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0, description=grade_desc))

    pros = data.xpath('//div[contains(@class, "verdict__pros")]/ul/li/p')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "verdict__cons")]/ul/li/p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "header")]/h2//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Verdict")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "verdict")]/p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Verdict")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "body")]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
