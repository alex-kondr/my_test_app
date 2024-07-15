from agent import *
from products.models import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.xda-developers.com/reviews/', use='curl'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h5[@class="display-card-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl'), process_review, dict(title=title, url=url))

    next_url = data.xpath('(//a[@class="infinite-btn-next main-cta primary-cta neutral-cta"]|//span[@class="current"]/following-sibling::a[1])/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.utl = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "author")]/text()').string()
    author_url = data.xpath('//a[contains(@class, "author")]/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="display-card-rating"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//ul[@class="pro-list"]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="con-list"]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)
