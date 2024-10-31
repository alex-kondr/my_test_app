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
    session.queue(Request('https://www.volkskrant.nl/ajax/recensies/film/leesmeer/1', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//a[@class="teaser__link"]')
    for rev in revs:
        title = rev.xpath('.//h3[contains(@class, "teaser__title")]//text()').string(multiple=True)
        cat = rev.xpath('.//span[contains(@class , "teaser__label")]//text()').string(multiple=True)
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, cat=cat, url=url))

    if revs:
        next_page = context.get('page', 1) + 1
        session.queue(Request('https://www.volkskrant.nl/ajax/recensies/film/leesmeer/' + str(next_page), use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].split('~')[-1].split('%7E')[-1]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="author"]/@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@data-test-id="article-sublabel" and contains(., "★")]//text()').string(multiple=True)
    if not grade_overall:
        grade_overall = data.xpath('(//p[regexp:test(., "^★")])[1]//text()').string(multiple=True)

    if grade_overall:
        grade_overall = float(grade_overall.count('★'))
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    summary = data.xpath('//p[@data-test-id="header-intro"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@class="paywall"]/p[not(contains(., "Geselecteerd door de redactie"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
