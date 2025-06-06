from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://gizmodo.com/reviews', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//li[contains(@class, "first")]')
    for rev in revs:
        cat = rev.xpath('.//span[contains(@class, "text") and span]/text()[not(contains(., "Reviews"))]').string()
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

    if not name:
        return

    product.name = re.sub(r' Review$| Reviewed$', '', name.replace('Gizmodo Reviews:', '').split(' Review: ')[0]).strip()

    if context.get('cat'):
        product.category = context['cat'].replace('Other', '').strip()
    else:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[contains(@class, "entry-title")]//text()').string(multiple=True)
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
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

    pros = data.xpath('//div[p[contains(., "Pros")]]/ul/li')
    if not pros:
        pros = data.xpath('//p[contains(., "LIKE")]/following-sibling::p[not(preceding-sibling::p[regexp:test(., "NO LIKE")] or regexp:test(., "NO LIKE"))]')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[p[contains(., "Cons")]]/ul/li')
    if not cons:
        cons = data.xpath('//p[contains(., "NO LIKE")]/following-sibling::p[not(preceding-sibling::p[regexp:test(., "Should .+ Buy .+?", "i")] or regexp:test(., "Should .+ Buy .+?", "i"))]')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "post-excerpt")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[contains(@class, "review")]//p[contains(@class, "text-lg")]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//h3|//p)[regexp:test(., "Should .+ Buy .+?", "i")]/following-sibling::p[not(preceding-sibling::h4 or preceding-sibling::*[contains(., "Specs")] or regexp:test(., "https:|Specs"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h3|//p)[regexp:test(., "Should .+ Buy .+?", "i")]/preceding-sibling::p[not(preceding-sibling::p[regexp:test(., "LIKE|NO LIKE")] or regexp:test(., "LIKE|NO LIKE"))][not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(@class)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
