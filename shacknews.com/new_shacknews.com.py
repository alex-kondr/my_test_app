from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.shacknews.com/topic/review', force_charset='utf-8', ), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//a[@class="article-title"]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(url=url))

    nexturl = data.xpath('//a[contains(@class, "load-more")]/@href').string()
    if nexturl:
        session.queue(Request(nexturl), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    title = data.xpath('//h1[@class="article-title"]/text()').string()

    product = Product()
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1].replace('-review-score', '').replace('-review', '')
    product.category = 'Games'

    product.name = data.xpath('//div[@class="review-header"]/div/a/text()').string()
    if not product.name:
        product.name = title.replace(' Review', '').replace('Mini-Review', '').replace(' Reviews', '').split('review: ')[0].split('review -')[0].split(' Review: ')[0].split('Review-in-Progress: ')[-1].strip()

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="by-line"]//a/text()').string()
    author_url = data.xpath('//div[@class="by-line"]//a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="score"]//text()').string(multiple=True)
    if grade_overall and grade_overall.isdigit() and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[@class="pros"]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–►…')
            if len(pro):
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="cons"]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–►…')
            if len(con):
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="article-lead-middle"]//p/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[contains(@class, "article-content")]/p[not(preceding-sibling::hr)]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
