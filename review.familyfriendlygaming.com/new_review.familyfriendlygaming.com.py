from agent import *
from models.products import *
import re
import time


SLEEP = 2


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.familyfriendlygaming.com/Reviews%20listing.html', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    time.sleep(SLEEP)

    cats = data.xpath('//div[@id="content"]//a[text()[string-length(normalize-space(.))>1]]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    time.sleep(SLEEP)

    revs = data.xpath('//td[@align="LEFT"]/a')
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, max_age=0), process_review, dict(context, name=name, url=url))


def process_review(data, context, session):
    time.sleep(SLEEP)

    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '').replace('%20', '_')
    product.category = 'Games' + '|' + context['cat']

    product.name = context['name']
    if not product.name:
        product.name = data.xpath('//h1[@class="center"]//text()').string(multiple=True)

    platforms = data.xpath('//p//text()[contains(., "System:")]').string()
    if platforms:
        product.category = 'Games' + '|' + platforms.replace('System:', '').replace('(tested)', '').strip()

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

    grade_overall = data.xpath('//p[contains(text(), "SCORE:")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.replace('SCORE:', '').strip()
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//p[regexp:test(., "\:.+\d+.%")]//text()').string(multiple=True)
    if grades:
        grades = re.findall(r'([\w\s/]+): (\d{2})', grades)
        for grade_name, grade_val in grades:
            grade_name = grade_name.strip()
            if grade_name and grade_val and float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100.0))

    excerpt = data.xpath('//div[@id="content"]/p[not(@class or @style or regexp:test(., "\:.+\d+.%|@familyfriendlygaming.com|Want more"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
