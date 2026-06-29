from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request('https://www.nintendoworldreport.com/review'), process_category, dict())


def process_category(data, context, session):
    letters = data.xpath('//div[@id="byLetter"]/ul/li/a[not(contains(., "All"))]')
    for letter in letters:
        letter = letter.xpath('text()').string()
        url = 'https://www.nintendoworldreport.com/review?letter=' + letter + '&sort=Post+Date&region=All&system=All&status=All&subsystem=All'
        session.queue(Request(url), process_revlist, dict(context))


def process_revlist(data, context, session):
    revs = data.xpath('//table[@id="results"]/tr[td]')
    for rev in revs:
        name = rev.xpath('td/a[not(@class)]/text()').string()
        platform = rev.xpath('td/a[@class]/text()').string()
        url = rev.xpath('td/a[text() and not(@class)]/@href').string()
        session.queue(Request(url), process_review, dict(name=name, platform=platform, url=url))


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Games|' + context['platform']
    product.manufacturer = data.xpath('//tr[contains(td/text(), "Developer")]/td[not(@class)]//text()').string(multiple=True)

    genre = data.xpath('//tr[contains(td/text(), "Genre")]/td[not(@class)]/text()').string()
    if genre:
        product.category += '|' + genre

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//div[@id="main"]/h3/text()').string()
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//span[@class="when"]/text()').string(multiple=True)
    if date:
        review.date = date.rsplit(', ', 1)[0]

    author = data.xpath('//a[contains(@title, "Profile for ")]/text()').string(multiple=True)
    author_url = data.xpath('//a[contains(@title, "Profile for ")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@id="article"]/div[@class="score"]/div/text()').string()
    if grade_overall and grade_overall[0].isdigit() and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades_name = data.xpath('//table[@id="scores"]/tr[1]/th[not(contains(., "Final"))]')
    grades_val = data.xpath('//table[@id="scores"]/tr[2]/td[not(@class)]')
    for grade_name, grade_val in zip(grades_name, grades_val):
        grade_name = grade_name.xpath('text()').string()
        grade_val = grade_val.xpath('text()').string()
        if grade_name and grade_val and grade_val[0].isdigit() and float(grade_val) > 0:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('//div[contains(h5, "Pros")]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(h5, "Cons")]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="biline"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[normalize-space(text())="Conclusion"]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@id="scorespage"]/p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[normalize-space(text())="Conclusion"]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="body"]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
