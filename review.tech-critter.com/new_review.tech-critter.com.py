from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.tech-critter.com/category/reviews-unboxings/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href|//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('Quick Overview on the ')[-1].split('Unboxing & Review: ')[-1].split('Review – be quiet! ')[-1].split(' Hands-On Review')[0].split('Quick Review: ')[-1].split('Unboxing & Preview – ')[-1].split('First Look – ')[-1].split('First Impression – ')[-1].split('Hands On – ')[-1].split('First Look: ')[-1].split("Review – ")[-1].split(' Review:')[0].split('Overview – ')[-1].split(' Overview')[0].split('Buy: ')[-1].split('eview: ')[-1].split(' – ')[0].split(' Review')[0].split(': ')[0]
    product.ssid = context['url'].split("/")[-2]

    product.url = data.xpath('//h2[contains(., "Where To Buy") or contains(., "Where to buy")]/following-sibling::ul/li/a/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = data.xpath('//meta[@property="article:section"]/@content[not(contains(., "Reviews"))]').string()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("//h4[contains(@class, 'author-box')]/text()").string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_list = {'Gold': 3, 'Silver': 2, 'Bronze': 1}
    grade_text = data.xpath("//img[regexp:test(@src, 'Bronze|Silver|Gold')]/@data-image-title").string()
    if grade_text and grade_text.split('Critter ')[-1] in grade_list:
        grade_overall = grade_list[grade_text.split('Critter ')[-1]]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=3.0))

    pros = data.xpath('//li[contains(., "Pros:")]/ul/li')
    if not pros:
        pros = data.xpath('(//p[normalize-space(b/text())="Pros"]/following-sibling::ul)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//li[contains(., "Cons:")]/ul/li')
    if not cons:
        cons = data.xpath('(//p[normalize-space(b/text())="Cons"]/following-sibling::ul)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    is_recommended = data.xpath('//img[regexp:test(@src, "Recommended")]')
    if is_recommended:
        review.add_property(type='is_recommended', value=True)

    conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p[not(contains(b, "Pros") or contains(b, "Cons"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[contains(., "Final Thoughts")]/following-sibling::p[not(contains(b, "Pros") or contains(b, "Cons"))]//text()')

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "container")]/div/p[not(preceding::h2[contains(., "Conclusion")] or preceding::h3[contains(., "Final Thoughts")])]')
    if not excerpt:
        excerpt = data.xpath('(//div[contains(@class, "container")]/p|//div[contains(@class, "container")]/div)[not(preceding::h2[contains(., "Conclusion")] or preceding::h3[contains(., "Final Thoughts")] or .//ul or .//li)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
