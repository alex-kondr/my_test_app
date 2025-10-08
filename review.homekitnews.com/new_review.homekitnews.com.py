from agent import *
from models.products import *


XCAT = ['apple', 'aqara', 'eve', 'mi', 'mijia', 'hpm', 'reviews', 'lifesmart', 'd-link', 'vocolinc', 'youtube', 'ikea', 'velux', 'wozart', 'opus', 'ge', 'athom', 'philips', 'zemismart', 'how to...']


def run(context, session):
    session.queue(Request('https://homekitnews.com/category/reviews/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="cm-entry-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('//h2[@class="cwp-item"]/text()').string() or context['title'].split(' (review')[0].replace('(installation and review)', '').replace('(Review)', '').strip()
    product.url = data.xpath('//div[contains(@class, "affiliate-button")]/a/@href').string() or context['url']
    product.ssid = context['url'].split('/')[-2].replace('-review', '')

    category = ''
    cats = data.xpath('//a[@rel="category tag"]/text()[normalize-space(.)]')
    for cat in cats:
        cat = cat.string()
        if cat.lower() not in XCAT:
            category += cat + '|'

    product.category = category.replace('/', ' ').replace(' | ', '|').strip(' |') if category else 'Tech'

    review = Review()
    review.title = context['title']
    review.url = context['url']
    review.type = 'pro'
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "author")]/a[not(contains(@href, "simon"))]/text()').string()
    author_url = data.xpath('//span[contains(@class, "author")]/a[not(contains(@href, "simon"))]/@href').string()
    if author:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))

    grade_overall = data.xpath('//div[contains(@class, "grade-content")]//span/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//div[@class="rev-option"]')
    for grade in grades:
        name = grade.xpath('div/h3//text()').string()
        value = grade.xpath('div/span/text()').string(multiple=True)
        if value:
            value = value.split('/')[0]
            review.grades.append(Grade(name=name, value=float(value), best=10.0))

    pros = data.xpath('//div[@class="pros"]/ul/li[normalize-space(.)]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="cons"]/ul/li[normalize-space(.)]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[contains(@class, "entry-summary")]//p[preceding-sibling::p[regexp:test(., "conclusion:", "i") or regexp:test(., "in conclusion", "i") or contains(., "CONCLUSION")] and not(contains(., "Full disclosure:"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "entry-summary")]//p[contains(., "CONCLUSION") and not(contains(., "Full disclosure:"))]/text()').string()
    if not conclusion:
        conclusion = data.xpath('(//h5|//p)[contains(., "SUMMING UP")]/following-sibling::p[not(contains(., "Full disclosure:"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(., "IN SUMMARY")]/following-sibling::p[not(contains(., "Full disclosure:"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h5|//p)[contains(., "SUMMING UP")]/preceding-sibling::p[not(contains(., "Full disclosure:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(., "IN SUMMARY")]/preceding-sibling::p[not(contains(., "Full disclosure:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-summary")]//p[not(preceding-sibling::p[regexp:test(., "conclusion:", "i") or contains(., "CONCLUSION") or regexp:test(., "in conclusion", "i")])][not(regexp:test(., "conclusion:", "i") or contains(., "CONCLUSION") or regexp:test(., "in conclusion", "i") or a[regexp:test(., ".\w")] or contains(., "Full disclosure:"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
