from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.gizguide.com/search/label/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="post-title entry-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@href, "reviews?updated-max=")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' - ')[0].split(', First ')[0].split('Review -')[0].replace('REVIEW:', '').replace('Review', '').replace('Unboxing', '').replace('See our review here!', '').replace('review', '').strip(' ,')
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html' , '')
    product.category = 'Tecno'

    cats = data.xpath('//a[@rel="tag"]/text()[not(contains(., "reviews") or contains(., "Review") or contains(., "tecno") or contains(., "news") or contains(., "News"))]').strings()
    if cats:
        product.category = '|'.join([cat.replace('review', '').strip().title() for cat in cats])

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//abbr[@class="published"]/@title').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/@title').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[contains(., "Average - ")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.split('-')[-1].split('/')[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//span[@style and regexp:test(., "^[\w/\s]+[\s]?- [\d\.]+$")]')
    for grade in grades:
        print(grade.xpath('.//text()').string(multiple=True).split(' - '))
        grade_name, grade_val = grade.xpath('.//text()').string(multiple=True).split('-')
        review.grades.append(Grade(name=grade_name.strip(), value=float(grade_val), best=5.0))

    pros = data.xpath('//span[b[contains(., "Pros")]]')
    if not pros:
        pros = data.xpath('//div[span/b[contains(., "Pros")]]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' -,Pros')
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[b[contains(., "Cons")]]')
    if not cons:
        cons = data.xpath('//div[span/b[contains(., "Cons")]]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(' -,Cons')
        review.add_property(type='cons', value=con)

    summary = data.xpath('//b/span[@style="font-family: helvetica;"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Quick thoughts")]/following-sibling::div/span[not(.//i or contains(., "Update:") or contains(., "Cons:") or contains(., "Pros:"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Verdict")]/following-sibling::div/span[not(.//i or contains(., "Update:") or contains(., "Cons:") or contains(., "Pros:"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Quick thoughts")]/preceding::div[@style and not(@class)]/span[not(.//i or @typeof or b[contains(., "Cons") or contains(., "Pros")] or contains(., "Update:") or contains(., "See also:") or contains(., "Cons:") or contains(., "Pros:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Verdict")]/preceding::div[@style and not(@class)]/span[not(.//i or @typeof or b[contains(., "Cons") or contains(., "Pros")] or contains(., "Update:") or contains(., "See also:")  or contains(., "Cons:") or contains(., "Pros:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@style and not(@class)]/span[not(.//i or @typeof or b[contains(., "Cons") or contains(., "Pros")] or contains(., "Update:") or contains(., "See also:") or contains(., "Cons:") or contains(., "Pros:"))]//text()').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        if excerpt and len(excerpt) > 2:

            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
