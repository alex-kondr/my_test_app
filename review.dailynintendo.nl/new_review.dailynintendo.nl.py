from agent import *
from models.products import *


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
    session.queue(Request('https://dailynintendo.nl/category/reviews/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('[Review]', '').replace('[Preview]', '').replace('3DS Review: ', '').replace('3DS eShop Review: ', '').replace('Wii Review: ', '').replace('3DS Video Review: ', '').replace('DS Review: ', '').replace('Wii/3DS review: ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('review-', '')
    product.category = 'Spellen'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "post-author-name")]/a/text()').string()
    author_url = data.xpath('//div[contains(@class, "post-author-name")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "review-final-score")]/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('(//strong|//p)[regexp:test(., "Eindcijfer|Totaal")]/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('//li[regexp:test(., "Eindcijfer|Totaal")]/text()').string()

    if grade_overall:
        grade_overall = float(grade_overall.split(':')[-1].strip().rsplit()[-1].replace(',', '.'))
        if grade_overall > 10:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))
        else:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//li[@class="blocks-gallery-item"]//img/@alt')
    if not grades:
        grades = data.xpath('(//strong|//p)[regexp:test(., "\w+: \d{1,2}[\.,]?/10?")]/text()')
    if not grades:
        grades = data.xpath('//li[regexp:test(., "\w+ \d{1,2}[\.,]?/10") and not(regexp:test(., "Totaal|Eindcijfer"))]/text()')
    if not grades:
        grades = data.xpath('//strong[regexp:test(., ".+\d{1,2}[\.,]?(/10)?") and not(regexp:test(., "Totaal|Eindcijfer"))]/text()')

    for grade in grades:
        grade = grade.string().replace('Review ', '').strip()
        if ':' in grade:
            grade_name, grade_val = grade.split(':')
        else:
            grade_name, grade_val = grade.split(' ', 1)

        try:
            grade_val = float(grade_val.replace(',', '.').split('/')[0])
            review.grades.append(Grade(name=grade_name, value=grade_val, best=10.0))
        except:
            pass

    conclusion = data.xpath('(//h2|//p)[regexp:test(., "conclusie", "i")]/following-sibling::p[not(regexp:test(., "Graphics|Gameplay|Eindcijfer|Beoordeling|Geluid|Speelduur|Totaal"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "review-summary-content")]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2|//p)[regexp:test(., "conclusie", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "post-content")]/p[not(regexp:test(., "Graphics|Gameplay|Eindcijfer|Beoordeling|Geluid|Speelduur|Totaal"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
