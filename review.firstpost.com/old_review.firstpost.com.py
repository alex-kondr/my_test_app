from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.firstpost.com/tech/reviews'), process_revlist, {})


def process_revlist(data, context, session):
    revs = data.xpath('//h3[@class="main-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = context['url'].split('-')[-1].split('.html')[0]
    product.category = 'Tech'

    name = context['title'].split('Review:')[0].split('review:')[0].strip()
    product.name = name if name else context['title']

    review = Review()
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.type = "pro"

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="author-info"]').first()
    if author:
        author_name = author.xpath('a/span/text()').string()
        author_url = author.xpath('a/@href').string()
        if author_name and author_url:
            author_ssid = author_url.split('/')[-1]
            review.authors.append(Person(name=author_name, ssid=author_ssid, url=author_url))

    pros = data.xpath('//p[strong[contains(., "Pros:")]]/text()')
    if not pros:
        pros = data.xpath('//p[contains(., "Buy the") and contains(., "if you")]/following-sibling::ul/li/text()')
    for pro in pros:
        pro = pro.string().strip(' -–')
        review.properties.append(ReviewProperty(name="Pros", type="pros", value=pro))

    cons = data.xpath('//p[strong[contains(., "Cons:")]]/text()')
    if not cons:
        cons = data.xpath('//p[contains(., "Don’t buy the") and contains(., "if you")]/following-sibling::ul/li/text()')
    for con in cons:
        con = con.string().strip(' -–')
        review.properties.append(ReviewProperty(name="Pros", type="pros", value=con))

    grades = data.xpath('//p[b[regexp:test(., "\d/\d")][not(contains(., "Rating:"))]]/b/text()')
    for grade in grades:
        grade = grade.string()
        if '(' in grade.split(': ')[-1]:
            grade_name = grade.split(':')[-1].split('-')[0].split('(')[0].strip()
            grade_value = grade.split(':')[-1].split('-')[0].split('(')[-1].split('/')[0].strip()
        else:
            grade_name = grade.split(':')[0].split('-')[0].strip()
            grade_value = grade.split(':')[-1].split('-')[-1].split('/')[0].strip()
        if grade_name and grade_value and grade_value.isdigit():
            review.grades.append(Grade(name=grade_name, value=float(grade_value), best=10.0))

    grade_overall = data.xpath('//p[contains(., "Rating:")]//text()[regexp:test(., "\d/\d")]').string()
    if grade_overall:
        value = grade_overall.split(':')[-1].split('/')[0].strip()
        max_value = grade_overall.split(':')[-1].split('/')[-1].split('(')[0].strip()
        if value and value.isdigit():
            review.grades.append(Grade(type="overall", value=float(value), best=float(max_value)))

    summary = data.xpath('//h2[@class="inner-copy"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//*[regexp:test(., "^verdict", "i")]//following-sibling::p[not(@*)][not(contains(., "Buy the") and contains(., "if you"))][not(contains(., "Don’t buy the") and contains(., "if you"))]//text()').string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type="conclusion", value=conclusion))

    excerpt = data.xpath('//div[@class="inner-copy article-full-content"]/p[not(contains(., "Pros:") or contains(., "Cons:") or contains(., "Rating:") or contains(., "Pricing:"))][not(regexp:test(., "\d/\d"))][not(contains(., "Rating:"))][not(a and contains(., "Read our "))]//text()[not(contains(., "Review: "))][not(preceding::*[regexp:test(., "^verdict", "i")])][not(regexp:test(., "^verdict", "i"))]').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '')

        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)
        session.emit(product)
