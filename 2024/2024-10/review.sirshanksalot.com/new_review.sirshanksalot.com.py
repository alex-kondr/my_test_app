from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://sirshanksalot.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('(//ul[not(li[ul]) and li/a[contains(., " Reviews")]])[1]//a[contains(., " Reviews")]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "gb-headline-text")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' Reviews', '').replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = context['cat'].replace('Reviews', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@href, "/author/")]/text()').string()
    author_url = data.xpath('//a[contains(@href, "/author/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[regexp:test(., "– ?\d+ ?%") and (contains(., "Combined ") or contains(., "Overall Rating"))]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.split('–')[-1].replace('%', '').strip()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//p[regexp:test(., "– ?\d+ ?%") and not(contains(., "Combined "))]')
    for grade in grades:
        grade_name, grade_value = grade.xpath('.//text()').string(multiple=True).split('–')
        grade_name = grade_name.replace('Overall', '').replace('Rating', '').strip()
        grade_value = grade_value.replace('%', '').strip()
        if grade_name and grade_value:
            review.grades.append(Grade(name=grade_name, value=float(grade_value), best=100.0))

    excerpt = data.xpath('(//div[@itemprop="text"]/div|//div[@itemprop="text"]//p)[not((contains(., "Overall ") and contains(., " Rating")) or contains(., "On eBay") or contains(., "Titleist Links"))]//text()').string(multiple=True)
    if excerpt:
        if 'Conclusion' in excerpt:
            excerpt, conclusion = excerpt.split('Conclusion')

            review.add_property(type='conclusion', value=conclusion.strip())

        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
