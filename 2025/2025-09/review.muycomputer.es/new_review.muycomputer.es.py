from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.muycomputer.com/analisis/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//li[contains(@class, "infinite-post")]')
    for rev in revs:
        title = rev.xpath('.//h2/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(',')[0].replace('Review ', '').replace('Test ', '').replace('Análisis de', '').replace('Análisis ', '').replace('(Developer Preview 4)', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@property="ratingValue"]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.replace(',', '.')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    if not grade_overall:
        grade_overall = data.xpath('//img[contains(@title, "stars")]/@title').string()
        if grade_overall:
            grade_overall = grade_overall.replace('stars', '').replace(',', '.')
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//div[contains(@class, "scores")]/div')
    for grade in grades:
        grade_val = grade.xpath('.//span[contains(@class, "score")]/text()').string()
        grade_name = grade.xpath('.//span[contains(@class, "label")]/text()').string()
        if grade_val and grade_name:
            grade_val = grade_val.replace(',', '.')
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('//div[contains(@class, "pros")]/text()').string(multiple=True, strip=False, normalize_space=False)
    if pros:
        pros = pros.split('\n')
        for pro in pros:
            pro = pro.strip(' +-*\n\t')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "cons")]/text()').string(multiple=True, strip=False, normalize_space=False)
    if cons:
        cons = cons.split('\n')
        for con in cons:
            con = con.strip(' +-*\n\t')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('(//h2|//h3|//p)[regexp:test(., "Conclusión|Conclusiones")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@property="reviewBody"]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('((//h2|//h3|//p)[regexp:test(., "Conclusión|Conclusiones")])[1]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@id, "content")]/p//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
