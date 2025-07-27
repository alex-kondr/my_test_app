from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('http://es.gizmodo.com/tag/analisis', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//li[contains(@class, "first")]')
    for rev in revs:
        cat = rev.xpath('.//span[contains(@class, "text-main")]/text()[not(contains(., "Reviews"))]').string()
        url = rev.xpath('.//a[@class="block"]/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(cat=cat, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]

    name = data.xpath('//div[contains(@class, "review")]//p[contains(@class, "text-main")]/text()').string()
    if not name:
        name = data.xpath('//h1[contains(@class, "entry-title")]/i/text()').string()
    if not name:
        name = data.xpath('//h1[contains(@class, "entry-title")]//text()').string(multiple=True)

    product.name = re.sub(r' Review$| Reviewed$|Análisis del ', '', name.replace('Gizmodo Reviews:', '').split(' Review: ')[0]).strip()

    if context.get('cat'):
        product.category = context['cat'].replace('Otro', '').strip()
    else:
        product.category = 'Tecnología'

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//meta[@property="article:published_time"]/@content').string(multiple=True)
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content|//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "author vcard")]//a[@rel="author"]/text()').string()
    author_url = data.xpath('//div[contains(@class, "author vcard")]//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count(//i[@class="fas fa-star"]) + count(//i[contains(@class, "fa-star-half")]) div 2')
    if grade_overall:
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//li[p[contains(text(), "Nos gusta")]]/p[not(contains(text(), "Nos gusta"))]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//li[p[contains(text(), "No nos gusta")]]/p[not(contains(text(), "No nos gusta"))]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "post-excerpt")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h3|//p)[regexp:test(., "En resumen", "i")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h3|//p)[regexp:test(., "En resumen", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(@class)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
