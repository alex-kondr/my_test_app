from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.androidpit.de/tests'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="article-teaser__link"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if '[Videos]' not in title and '[Video]' not in title:
            session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//li[contains(@class, "page--next")]/a/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(': Schneller Test')[0].split(':1 im Test:')[0].split(': Test ')[0].split(': Mein Langzeit-Test')[0].split('Honeycomb Tablet')[0].split(': ein Erfahrungsbericht')[0].split(' im ')[0].split(':')[-1].split('besteht Langzeit-Test')[0].replace(' Test', '').replace('PureView', '').replace('Test der bunten ', '').replace('[Videos]', '').replace('[Video]', '').replace('[UserReview]', '').replace('[AndroidPIT Exklusiv]', '').replace('von Kamera-Tests', '').replace('[Review]', '' ).replace('[REVIEW]', '').replace('Review', '').replace('[Hands-On]', '').replace('[IFA 2010]', '').replace('Produkttest', '').replace('Gadget Review - ', '').strip()
    product.ssid = context['url'].split('/')[-1]

    product.url = data.xpath('//span[@class="np-offer__link np-offer__link--AMAZON"]/@data-href').string()
    if not product.url:
        product.url = context['url']

    cats = data.xpath('//div[@class="articleContentWrapper"]/ul/li/a/text()[not(contains(., "Home") or contains(., "Mehr"))]').strings()
    if cats:
        product.category = '|'.join(cats)
    else:
        product.category = 'Technik'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time[@class="articlePublishedDate"]/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="articleAuthorName"]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="ratingStars"]/use/@href').string()
    if grade_overall:
        grade_overall = float(grade_overall.split('stars-')[-1]) / 2
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//ul[@class="goodList"]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).replace('-', '').replace('/', '').strip()
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="badList"]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).replace('-', '').replace('/', '').strip()
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="articlePartIntroContent"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[@class="finalVerdictDesc"]/p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "articlePartContent")]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
