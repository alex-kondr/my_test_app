from agent import *
from models.products import *


def run(context, session):
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
        product.category = category.replace('Tests -', '').strip()
    else:
        product.category = 'Technologie'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    rev_json = data.xpath('//script[contains(., "dateCreated")]/text()').string()
    if rev_json:
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
        author = data.xpath('')

    grade_overall = data.xpath('//text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=))

    pros = data.xpath('(//h3[contains(., "Pros")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[contains(., "Cons")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[h3[contains(text(), "Summary")]]/div//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
