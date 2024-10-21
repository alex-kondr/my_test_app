from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://bgr.com/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2//a[@href and text()]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' review: ')[0].strip()
    product.ssid = context['url'].split('/')[-2]

    product.url = data.xpath('//a[contains(@rel, "sponsored")]/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = data.xpath('//div[contains(@class, "bgr-breadcrumbs")]//a[not(regexp:test(., "Home|Reviews"))]/text()').string()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:modified_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "authors")]//a[@rel="author"]/text()').string()
    author_url = data.xpath('//div[contains(@class, "authors")]//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[contains(., "Rating:")]/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.split(':')[-1].split()[0])
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//ul[@class="pros"]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="cons"]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="flex justify-between"]//p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[@id="h-conclusions" or regexp:test(., "conclusion|final", "i")]/following::p[not(preceding::div[@class="mb-8 relative"])]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[@id="h-conclusions" or regexp:test(., "conclusion|final", "i")]/preceding::body/p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
