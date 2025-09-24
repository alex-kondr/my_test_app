from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://sectionhiker.com/category/gear-reviews-2/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' Review', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')

    product.url = data.xpath('//a[contains(., "Shop")]/@href').string()
    if not product.url:
        product.url = context['url']

    category = data.xpath('//a[@rel="category tag"]/text()').string()
    if category:
        product.category = category.replace(' Reviews', '').strip()
    else:
        product.category = 'Backpacking Gear'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="post-meta-author"]//text()').string(multiple=True)
    author_url = data.xpath('//span[@class="post-meta-author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review-final-score"]//span/@style').string()
    if grade_overall:
        grade_overall = round(float(grade_overall.replace('width:', '').replace('%', '')) / 20, 1)
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    grades = data.xpath('//div[@class="review-item"]')
    for grade in grades:
        grade_name = grade.xpath('h5/text()').string()
        grade_val = round(float(grade.xpath('.//span/@style').string().replace('width:', '').replace('%', '')) / 20, 1)
        review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    pros = data.xpath('(//h4[contains(., "Who should buy them")]/following-sibling::*)[1]/li')
    if not pros:
        pros = data.xpath('(//h3[contains(., "Who it’s for")]/following-sibling::*)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h4[contains(., "Who should skip them")]/following-sibling::*)[1]/li')
    if not cons:
        cons = data.xpath('(//h3[contains(., "What it’s not")]/following-sibling::*)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "Recommendation")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    summary = data.xpath('//div[@class="review-short-summary"]/p//text()').string()
    if conclusion and summary:
        review.add_property(type='summary', value=summary)

    if not conclusion and summary:
        review.add_property(type='conclusion', value=summary)

    excerpt = data.xpath('//h2[contains(., "Recommendation")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry"]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
