from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('http://www.top-for-phone.fr/category/tests', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//span[contains(@id, "next-page")]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split("Test du")[-1].split(":")[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]

    category = data.xpath('//a[contains(@href, "/category/") and @property="v:title"]/text()').string()
    if category:
        product.category = category.replace('Tests -', '').strip().title()
    else:
        product.category = 'Technologie'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    rev_json = data.xpath('//script[contains(., "dateCreated")]/text()').string()
    if rev_json:
        rev_json = simplejson.loads(rev_json)

        date = rev_json.get('datePublished')
        if date:
            review.date = date.split("T")[0]

        author = rev_json.get('author', {}).get('name')
        author_url = rev_json.get('authot', {}).get('url')
        if author and author_url:
            author_ssid = author_url.split('/')[-1]
            review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

    if not review.authors:
        author = data.xpath('//section[contains(@id, "author")]/following-sibling::div[@class="block-head"]/h3/text()').string()
        if author:
            author = author.split(':')[-1].strip()
            review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review-final-score"]/h3/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//div[@class="review-item"]')
    for grade in grades:
        grade = grade.xpath('.//h5//text()').string(multiple=True)
        if grade:
            grade_name, grade_val = grade.split(' - ')
            grade_name = grade_name.strip()
            grade_val = grade_val.strip(' %')
            if grade_name and grade_val and float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100.0))

    pros = data.xpath('//li[strong[contains(., "Les plus")]]/text()[normalize-space(.)]')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//li[strong[contains(., "Les moins")]]/text()[normalize-space(.)]')
    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="review-short-summary"]/p//text()').string(multiple=True)
    conclusion = data.xpath('//h3[regexp:test(., "conclusion", "i")]/following-sibling::p[preceding-sibling::h3[1][regexp:test(., "conclusion", "i")] and not(preceding::strong[regexp:test(., "Les plus|Les moins")])]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

        if summary:
            review.add_property(type='summary', value=summary)

    elif summary:
        review.add_property(type='conclusion', value=summary)

    excerpt = data.xpath('//div[@class="entry"]/p[not(preceding::strong[regexp:test(., "Les plus|Les moins")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
