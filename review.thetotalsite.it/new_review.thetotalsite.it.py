from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.mumsnet.com/h/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="post-title entry-title"]/a')
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(name=name, url=url))


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Games'

    platforme = data.xpath('//font[contains(., "Piattaforma:")]/text()').string()
    genre = data.xpath('//font[contains(., "Genere:")]/text()').string()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="post-inner group"]//a[@rel="author"]/text()').string()
    author_url = data.xpath('//div[@class="post-inner group"]//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[regexp:test(normalize-space(.), "\d+\.?\d? ?/ ?\d+$") and contains(., "Globale")]//text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[not(@class or @id) and contains(., "Pro e contro")]/following-sibling::div[not(@class or @id) and regexp:test(normalize-space(.), "^\+")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[not(@class or @id) and contains(., "Pro e contro")]/following-sibling::div[not(@class or @id) and regexp:test(normalize-space(.), "^–")]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@align="center"]//font[@size="3"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[not(@class or @id or @align or regexp:test(normalize-space(.), "\d+\.?\d? ?/ ?\d+$"))]/span[@style="color: black"]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
