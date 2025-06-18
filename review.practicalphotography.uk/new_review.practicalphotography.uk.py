from agent import *
from models.products import *
import re


def run(context, session):
    session.queue(Request('http://www.practicalphotography.com/reviews', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[contains(@class, "title")]')
    for rev in revs:
        title = rev.xpath('.//text()').string(multiple=True)
        url = rev.xpath('@href').string()

        if not re.search(r'The best |Deal Days |Snappy savings:', title) and 'review' in title.lower():
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//li[@data-test="page->"]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' review', '').replace('Reviewed:', '').replace(': Review', '').replace(' Review', '').split(':')[-1].strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')

    product.url = data.xpath('//a[contains(., "Buy")]/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = data.xpath('//a[contains(@class, "breadcrumbs_breadcrumbs__link") and not(span)]/text()').string()
    if not product.category:
        product.category = 'Tech'

    manufacturer = data.xpath('//div[contains(@class, "product-brand")]/text()').string()
    if manufacturer:
        product.manufacturer = manufacturer.replace('from ', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "author")]//text()').string()
    author_url = data.xpath('//a[contains(@class, "author")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count(//div[@data-test="product-review-rating"]/div[contains(@class, "rating__not-full")]/span[contains(@class, "ratings_rating__on")])')
    if grade_overall:
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    if not grade_overall:
        grade_overall = data.xpath('//h2[contains(., "Score:")]//text()').string()
        if grade_overall:
            grade_overall = grade_overall.replace('Score:', '').split('/')[0].strip()
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//li[contains(@class, "product__ratings-item")]')
    for grade in grades:
        grade_name = grade.xpath('div[contains(@class, "ratings-item-child")]/text()|div[contains(@class, "ratings-item-child")]/span/span/text()').string()
        grade_val = grade.xpath('.//div[contains(@class, "stars-score")]//text()').string()
        if 'Overall' not in grade_name:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('//div[h3[contains(@class, "pros-title")]]/ul/li')
    if not pros:
        pros = data.xpath('//p[preceding-sibling::h3[1][regexp:test(., "Pros")]]')
    if not pros:
        pros = data.xpath('(//table[@class="review-table" and tr/th[contains(., "Pros")]])[1]/tr/td[1]')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[h3[contains(@class, "cons-title")]]/ul/li')
    if not cons:
        cons = data.xpath('//p[preceding-sibling::h3[1][regexp:test(., "Cons")] and not(.//strong)]')
    if not cons:
        cons = data.xpath('(//table[@class="review-table" and tr/th[contains(., "Cons")]])[1]/tr/td[2]')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[@data-test="subtitle"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Verdict")]/following-sibling::p[preceding-sibling::h2[1][contains(., "Verdict")]]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[.//strong[contains(., "Verdict:")]]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace('Verdict:', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Verdict")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content")]/p[not(preceding-sibling::h2[regexp:test(., "Who tested it?|Similar items to consider|Why should|How we test")] or contains(., "Verdict:") or preceding-sibling::h3[regexp:test(., "Pros|Cons")] or preceding-sibling::p[.//strong[contains(., "Want to find out more?")]])]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace('Verdict:', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
