from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://techtest.org/category/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "entry-title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('//div[regexp:test(@class, "^lets-review-block__title")]//text()').string(multiple=True)
    product.ssid = context['url'].split('/')[-2]

    product.url = data.xpath('//a[contains(., "Link zum Hersteller")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@class="tdb-author-name"]/text()').string()
    author_url = data.xpath('//a[@class="tdb-author-name"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="score"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[regexp:test(@class, "lets-review-block__pro$")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[regexp:test(@class, "lets-review-block__con$")]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="tdb-block-inner td-fix-index"]/p[not(preceding-sibling::div[@id="ez-toc-container"])]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)


    excerpt = data.xpath('//h2[contains(., "Fazit")]/preceding-sibling::p[preceding-sibling::div[@id="ez-toc-container"]]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

    conclusion = data.xpath('//h2[contains(., "Fazit")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

        product.reviews.append(review)

        session.emit(product)
