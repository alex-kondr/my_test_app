from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://tecnoblog.net/testamos/"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="grid4"]')
    for rev in revs:
        title = rev.xpath('.//h2/text()').string()
        date = rev.xpath('.//time/@datetime').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url), process_review, dict(title=title, date=date, url=url))

    next_url = data.xpath('//a[contains(., "Próxima")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('[Preview]', '').replace('[Review]', '').replace('o review de', '').replace('Preview: ', '').replace('Review: ', '').replace('Review ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Tecnologia'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    if context['date']:
        review.date = context['date'].split('T')[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@id="nota"]/span[not(@class)]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//div[@class="atr-nota"]')
    for grade in grades:
        grade_name = grade.xpath('div[@class="attr left"]/text()').string()
        grade_val = grade.xpath('div[@class="attr right"]/text()').string()
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('//h4[contains(., "Prós")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//h4[contains(., "Contras")]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="flipboard-subtitle olho"]//text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[@id="conclusao"]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[@id="conclusao"]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="review"]/p//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)