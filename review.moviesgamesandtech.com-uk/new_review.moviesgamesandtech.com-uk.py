from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request('https://moviesgamesandtech.com/category/reviews/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "entry-title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review:', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('review-', '')
    product.category = 'Gaming'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "post-author-name")]/a/text()').string()
    author_url = data.xpath('//span[contains(@class, "post-author-name")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "review-final-score")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('(//p|//h4|//h5)[contains(., "Pros:")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//div[contains(@class, "review-summary-content")]/text()[contains(., "+")]')
        for pro in pros:
            pro = pro.string().strip(' +-.*')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p|//h4|//h5)[contains(., "Cons:")]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//div[contains(@class, "review-summary-content")]/text()[contains(., "-")]')
        for con in cons:
            con = con.string().strip(' +-.*')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[regexp:test(., "Conclusion|Verdict|Final Thoughts")]/following-sibling::p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure", "i"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "review-summary-content")]/p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure|Rating:|Reviewed on", "i"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Conclusion|Verdict|Final Thoughts")]/preceding-sibling::p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure", "i"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "block-inner")]/p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure", "i"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
