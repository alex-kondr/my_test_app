from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.mundogamers.com/analisis/videojuegos', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="link_box"]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    last_page = data.xpath('//a[@aria-label="Last"]/@href').string()
    if last_page:
        last_page = int(last_page.split('/')[-1])
        current_page = context.get('page', 1)
        if current_page < last_page:
            next_page = current_page + 1
            next_url = 'https://www.mundogamers.com/analisis/videojuegos/{}'.format(next_page)
            session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Analisis ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]

    product.category = 'Games'
    platforms = data.xpath('//h1/text()').string()
    if platforms:
        platforms = platforms.split(',', 1)[-1].split(',')
        product.category += '|' + '/'.join(platforms)

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[@id="fecha"]/text()').string()
    if date:
        review.date = date.split(' ', 1)[-1].rsplit(' ', 1)[0].strip()

    author = data.xpath('//div[@id="fecha"]/b/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="box"]/text()').string(multiple=True)
    if grade_overall:
        grade_overall = float(grade_overall)
        if grade_overall > 10:
            grade_overall = 10.0

        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    summary = data.xpath('//div[@class="desc"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//*[contains(., "NOTA FINAL")]/following-sibling::text()[string-length() > 5]').string(multiple=True)
    if conclusion:
        conclusion = conclusion.strip(' *')
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//div[@id="cuerpo"]|//div[@id="cuerpo"]/div[contains(@class, "pagina")])/p[not(contains(., "(Versión analizada:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="cuerpo"]/text()|//div[@id="cuerpo"]/b//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="texto"]//text()').string(multiple=True)

    if excerpt and len(excerpt) > 5:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        excerpt = excerpt.strip(' *')
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
