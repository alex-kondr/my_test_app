from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.videogamer.com/reviews', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    if revs:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.videogamer.com/reviews/page/{}/'.format(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(page=next_page))


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].split(' review – ')[0].replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = 'Games'
    product.manufacturer = data.xpath('//p[strong[contains(., "Developer:")]]/text()').string(multiple=True)

    platforms = data.xpath('//li[@class="platform"]/b/text()').string()
    if platforms:
        product.category += '|' + platforms.replace(', ', '/')

    genres = data.xpath('//li[contains(., "Genre(s):")]/b/text()').string()
    if genres:
        product.category += '|' + genres.replace(', ', '/')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[@class="date"]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="author"]/span[not(@class)]//text()[not(contains(., "By"))]').string()
    author_url = data.xpath('//div[@class="author"]/span[not(@class)]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review--right"]/b/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//span[@class="yes"]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[@class="no"]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[@class="quote"]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="article__body"]/p[not(contains(., "Reviewed on "))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
