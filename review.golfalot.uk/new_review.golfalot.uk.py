from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://golfalot.com/equipment-review', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]//a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('-review', '')
    product.category = data.xpath('//a[@rel="tag"]/text()').join('|') or 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//ul[not(@data-id)]/li[@itemprop="datePublished"]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]//text()').string(multiple=True)
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@itemprop="ratingValue"]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.split('/')[0].replace(',', '.')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//div[contains(@class, "product-scores")]//li')
    for grade in grades:
        grade_name = grade.xpath('span/text()').string()
        grade_val = grade.xpath('.//span/@style').string()
        if grade_val:
            grade_val = float(grade_val.split(':')[-1].strip(' %;')) / 20
            review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    pros = data.xpath('//div[contains(@class, "review-pros")]//li')
    if not pros:
        pros = data.xpath('(//p[strong[normalize-space(text())="Pros"]]/following-sibling::ul)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).replace('�', '').strip()
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "review-cons")]//li')
    if not cons:
        cons = data.xpath('(//p[strong[normalize-space(text())="Cons"]]/following-sibling::ul)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).replace('�', '').strip()
        review.add_property(type='cons', value=con)

    conclusion = data.xpath('(//h2|//h3|//p)[regexp:test(., "Verdict|Would I Use It")]/following-sibling::p[not(@class)]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').replace('�', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('((//h2|//h3|//p)[regexp:test(., "Verdict|Would I Use It")])[1]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-content") and not(@itemprop)]/p[not(@class)]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').replace('�', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
