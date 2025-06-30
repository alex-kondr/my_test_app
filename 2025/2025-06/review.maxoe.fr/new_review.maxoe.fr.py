from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.maxoe.com/games/jeux-articles/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "title") or @class="unebox-text-3"]/a[@rel]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if not next_url:
        next_url = data.xpath('//a[contains(., "Suivante")]/@href').string()

    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('//div[@class="titlefiche"]/text()').string() or context['title'].split(':')[0].replace('', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Games'

    genres = data.xpath('//b[contains(., "Genre") and not(contains(., "Va Savoir"))]/following-sibling::text()').string()
    if genres:
        product.category += '|' + genres.strip(' .:').title().replace(', ', '/').replace(' - ', '/')

    platforms = data.xpath('//b[contains(., "Support")]/following-sibling::text()').string()
    if platforms:
        product.category += '|' + platforms.strip(' .:').replace(', ', '/').replace(',...', '').replace(' / ', '/')

    manufacturer = data.xpath('//b[contains(., "Développeur")]/following-sibling::text()').string()
    if manufacturer:
        product.manufacturer = manufacturer.strip(' :')

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//span[@class="titlepost titlegames"]//text()').string(multiple=True) or context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if not date:
        date = data.xpath('//span[a[@rel="author"]]/text()').string()
    if not date:
        date = data.xpath('//div[@class="row no-gutters"]//div[@class="addmargin-right"]/span/text()').string()

    if date:
        review.date = date.split('T')[0].split(',')[0].split('-')[-1].strip()

    author = data.xpath('//span[a[@rel="author"]]/a/text()').string()
    if not author:
        author = data.xpath('//div[@class="row no-gutters"]//div[@class="addmargin-right"]/span/text()').string()

    author_url = data.xpath('//span[a[@rel="author"]]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        author = author.split('-')[0].strip()
        review.authors.append(Person(name=author, ssid=author))

    grades = data.xpath('(//div[@class="row no-gutters-une"])[1]//center')
    for grade in grades:
        grade_name = grade.xpath('div[@class="avisfiche"]/text()').string().capitalize()
        grade_val = grade.xpath('.//img/@onmouseout').string()
        if grade_val:
            grade_val = float(grade_val.split('(')[-1].split(',')[0])
            if grade_val > 5:
                grade_val = 5.0

            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))
        else:
            grade_val = grade.xpath('.//img/@title').string()
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('//div[div[@class="onaaime"]]/div[contains(@class, "text")]/text()[not(contains(., ":"))]')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[div[@class="onamoinsaime"]]/div[contains(@class, "text")]/text()[not(contains(., ":"))]')
    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="cadregris" and @style]/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[@class="cadregris" and not(@style)]/text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="fullsingle singlegames"]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
