from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.meilleur-robot-tondeuse.fr/avis'), process_revlist, dict())


def process_revlist(data, context, session):
    prods = data.xpath('//h2[@class="elementor-post__title"]/a')
    for prod in prods:
        title = prod.xpath('.//text()').string(multiple=True)
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('//h5[@class="review-title"]/text()').string()
    product.ssid = context['url'].split('/')[-2].replace('-avis', '')
    product.category = 'Tech'

    product.url = data.xpath('//a[contains(@href, "https://amzn.to/")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[@class="entry-title"]/text()').string()
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="author-name"]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="review-total-box"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//ul[@class="review-list"]/li')
    for grade in grades:
        grade_name = grade.xpath('span/text()').string()
        grade_val = grade.xpath('.//div[contains(@style, "width")]/@style').string()
        if grade_val:
            grade_val = float(grade_val.split('%')[0].split(':')[-1]) / 20
            review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    pros = data.xpath('//div[@class="su-service" and contains(., "Avantages")]//li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="su-service" and contains(., "Inconvénients")]/following-sibling::div[@class="su-service"]//li')
    if not cons:
        cons = data.xpath('//div[@class="su-service" and contains(., "Inconvénients")]//li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//p[contains(., "Résumé")]/following-sibling::p[not(@align)]//text()').string(multiple=True)

    conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if conclusion and summary:
        review.add_property(type='summary', value=summary)

    elif not conclusion:
        conclusion = summary

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@itemprop="text"]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
