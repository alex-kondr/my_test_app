from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.familyfriendlygaming.com/Reviews%20listing.html'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@id="content"]//a[text()[string-length(normalize-space(.))>1]]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//td[@align="LEFT"]/a')
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, name=name, url=url))


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '')
    product.category = 'Games' + '|' + context['cat']

    platforms = data.xpath('//p//text()[contains(., "System:")]').string()
    if platforms:
        product.category = 'Games' + '|' + platforms.replace('System:', '').strip()

    manufacturer = data.xpath('//p//text()[contains(., "Developer:")]').string()
    if manufacturer:
        product.manufacturer = manufacturer.replace('Developer:', '').strip()

    images = data.xpath('//div[@id="content"]/p/img/@src')
    for image in images:
        image_url = image.string()
        if image_url:
          product.add_property(type='image', value=dict(type='product', src=image_url))

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//head/title/text()').string()
    review.url = product.url
    review.ssid = product.ssid

    author = data.xpath('//p//text()[contains(., "Publisher:")]').string()
    if author:
        author = author.replace('Publisher:', '').strip()
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[contains(text(), "SCORE:")]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.replace('SCORE:', '').strip()
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//p//text()[regexp:test(., "\: \d+%")]')
    for grade in grades:
        grade_name = grade.string().split(':')[0].strip()
        grade_val = grade.string().split(':')[-1].replace('%', '')
        if grade_name and grade_val and float(grade_val) > 0:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100.0))

    excerpt = data.xpath('//div[@id="content"]/p[not(@class or @style or @align)]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
