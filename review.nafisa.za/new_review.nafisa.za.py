from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.recharged.co.za/review/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[contains(@class, "title")]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if not next_url:
        next_url = data.xpath('//a[contains(@class, "next")]/@href').string()

    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    title = data.xpath('//h1/text()').string()
    product = Product()
    product.name = title.split(':')[-1].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('review-', '')

    cats = data.xpath('//div[@class="post-single-meta"]//div[@class="post-categories"]/a[not(contains(., "review"))]/text()').strings()
    if cats:
        product.category = '|'.join([cat.title() for cat in cats])
    else:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if not date:
        date = data.xpath('//div[@class="post-single-meta"]//a[@class="post-date"]/text()').string()

    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="post-single-meta"]//a[@class="post-author"]//text()').string()
    author_url = data.xpath('//div[@class="post-single-meta"]//a[@class="post-author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "score")]/h4//text()').string(multiple=True)
    if grade_overall:
        grade_overall = float(grade_overall.replace(' .', '.'))
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    grades = data.xpath('//div[contains(@class, "review-progressbar")]/div[@class="row"]')
    for grade in grades:
        grade_name = grade.xpath('div[not(contains(@class, "text"))]/text()').string()
        grade_val = grade.xpath('div[contains(@class, "text")]/text()').string()
        if grade_name and grade_val:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('//ul[contains(@class, "review-pros")]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[contains(@class, "review-cons")]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[contains(@class, "review-verdict")]/p//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "post-single-content")]/p//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
