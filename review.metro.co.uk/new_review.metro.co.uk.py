from agent import *
from models.products import *
import re


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://metro.co.uk/tag/games-reviews/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if not title.startswith('Best') and 'the best games' not in title.lower() and not re.search(r'all \d+ games so far', title):
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' full review – ')[0].split(' review - ')[0].replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].split('-')[-1]
    product.category = 'Tech'

    platforms = data.xpath('//p[contains(., "Formats:")]//text()[contains(., "Formats:")]').string()
    if platforms:
        product.category = 'Games|' + platforms.replace('Formats:', '').replace(' (reviewed)', '').replace(' and', '').replace(', ', '/').strip()

    manufacturer = data.xpath('//p[contains(., "Developer:")]//text()[contains(., "Developer:")]').string()
    if manufacturer:
        product.manufacturer = manufacturer.replace('Developer:', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@class="author-name" and not(contains(., "GameCentral"))]/text()').string()
    author_url = data.xpath('//a[@class="author-name" and not(contains(., "GameCentral"))]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[contains(., "Score:")]')
    if grade_overall and len(grade_overall) > 1:
        return

    if grade_overall:
        grade_overall = grade_overall[0].xpath('.//text()').string(multiple=True)
        grade_overall = float(grade_overall.split(':')[-1].split('/')[0])
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//p[contains(., "Pros:")]//text()[not(contains(., "Pros:"))]').string(multiple=True)
    if pros:
        pros = pros.strip(' +-*.:;•,–')
        if len(pros) > 1:
            review.add_property(type='pros', value=pros)

    cons = data.xpath('//p[contains(., "Cons:")]//text()[not(contains(., "Cons:"))]').string(multiple=True)
    if cons:
        cons = cons.strip(' +-*.:;•,–')
        if len(cons) > 1:
            review.add_property(type='cons', value=cons)

    conclusion = data.xpath('//p[contains(., "In Short:")]//text()[not(contains(., "In Short:"))]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="article__content__inner"]/p[not(preceding::p[regexp:test(., "Formats:|Publisher:|Developer:|MORE:|In Short:|Pros:|Cons:|Score:")] or regexp:test(., "Formats:|Publisher:|Developer:|MORE:|In Short:|Pros:|Cons:|Score:"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
