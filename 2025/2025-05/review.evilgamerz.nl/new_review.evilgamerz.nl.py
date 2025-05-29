from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://evilgamerz.com/category/review/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="entry-title"]/a')
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Games'
    product.manufacturer = data.xpath('//span[@title="Developer"]/following-sibling::text()').string()

    cats = data.xpath('//div[@class="post-cat"]//span[contains(@class, "category-button") and not(contains(., "Review") or contains(., "Uitgelicht"))]')
    if cats:
        product.category += '|' + '/'.join([cat.xpath('.//text()').string(multiple=True) for cat in cats])

    genre = data.xpath('//span[@title="Genre"]/following-sibling::text()').string()
    if genre:
        product.category += '|' + genre.split()[0]

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//meta[@property="og:title"]/@content').string()
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@title="Auteur"]/following-sibling::text()').string()
    if author and len(author.replace('/', '').strip()) > 1:
        author = author.replace('/', '').strip()
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@itemprop="ratingValue"]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.replace(',', '.').replace('..', '.').strip(' +-*.X')
        if len(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades_names = data.xpath('//div[@class="artikel_veld catpunten"]/text()').strings()
    grades_values = data.xpath('//div[@class="artikel_veld catpunten"]/b/text()').strings()
    for grade_name, grade_val in zip(grades_names, grades_values):
        if grade_val and grade_name:
            grade_name = grade_name.strip(' :')
            grade_val = grade_val.replace(',', '.').replace('..', '.').strip(' +-*.X')
            if len(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('//div[@class="plus_veld"]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' .+-*')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="min_veld"]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(' .+-*')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[@class="entry-content"]//p[contains(., "Verdict")]/following-sibling::p[not(.//b)]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\ufeff', ' ')
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="entry-content"]//p[not(.//b)]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\ufeff', ' ')

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
