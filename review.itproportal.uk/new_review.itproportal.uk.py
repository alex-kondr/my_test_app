from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.itpro.com/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    page = int(data.xpath('//span[@class="active"]/text()').string())
    if page != context.get('page', 1):
        return

    revs = data.xpath('//a[@class="article-link"]')
    for rev in revs:
        title = rev.xpath('@aria-label').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = 'https://www.itpro.com/reviews/page/' + str(page + 1)
    session.queue(Request(next_url), process_revlist, dict(page=page + 1))


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('//title/text()').string().replace('Review | ITPro', '').replace('review | ITPro', '').split('review:')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@name="pub_date"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="parsely-author"]/@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count(//div[@class="byline"]//span[@class="icon icon-star"])')
    if grade_overall and grade_overall > 0:
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//div[@class="pretty-verdict__pros"]//p')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="pretty-verdict__cons"]//p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="header-sub-container"]/h2//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@class="text-copy bodyCopy auto"]//p[not(@class or @style)]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
