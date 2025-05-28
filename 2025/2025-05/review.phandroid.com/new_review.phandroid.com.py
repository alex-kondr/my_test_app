from agent import *
from models.products import *


XCAT = ['Editors Choice', 'Reviews', 'reviews', 'Featured']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://phandroid.com/category/reviews/", use="curl", force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="list-item"]')
    for rev in revs:
        title = rev.xpath('.//h3/a/text()').string()
        url = rev.xpath('.//h3/a/@href').string()

        cat = rev.xpath('.//a[contains(@class, "cat-theme")]/text()').string()
        if cat not in XCAT:
            session.queue(Request(url, use="curl", force_charset='utf-8'), process_review, dict(title=title, url=url, cat=cat))

    next_url = data.xpath('//a[span[contains(@class, "next")]]/@href').string()
    if next_url:
        session.queue(Request(next_url, use="curl", force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' Review')[0].split(' review')[0].split('Review: ')[-1]
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat'].replace('News', 'Tech').replace('Deals', 'Tech')

    product.url = data.xpath('(//a[contains(@class, "product")]|//a[contains(., "Buy")])/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.type = 'pro'

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "author") and @rel="author"]/text()').string()
    author_url = data.xpath('//a[contains(@class, "author") and @rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="post-score-value"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    if not grade_overall:
        grade_overall = data.xpath('//span[@itemprop="ratingValue"][not(contains(., "X.X"))]/text()').string()
        if not grade_overall:
            grade_overall = data.xpath('//span[@itemprop="reviewRating"]/text()').string(multiple=True)
            if grade_overall and not grade_overall.split('(')[-1].split('/')[0].strip():
                grade_overall = ''
        if not grade_overall:
            grade_overall = data.xpath('count(//span[@itemprop="reviewRating"]/i[contains(., "star_full")])')

        if grade_overall:
            value = grade_overall.split('(')[-1].split('/')[0]
            review.grades.append(Grade(type='overall', value=float(value), best=5.0))

    pros = data.xpath('//div[@class="mnmd-review__pros"]//span')
    if not pros:
        pros = data.xpath('//div[@class="pros"]//li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' +-*.')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="mnmd-review__cons"]//span')
    if not cons:
        cons = data.xpath('//div[@class="cons"]//li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(' +-*.')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "summary")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "conclusion", "i") or regexp:test(., "final thoughts", "i")]//following-sibling::p[not(regexp:test(., "Note:|Disclaimer:"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[regexp:test(., "conclusion", "i") or regexp:test(., "final thoughts", "i")]//following-sibling::div[@class="pros-cons-container"]//p[not(regexp:test(., "Note:|Disclaimer:"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "entry-content")]//p[not(img)][not(.//strong[contains(., "Read:")])][not(preceding::h2[regexp:test(., "conclusion", "i") or regexp:test(., "final thoughts", "i")])][not(regexp:test(., "\[via", "i"))][not(regexp:test(., "Note:|Disclaimer:"))]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace('\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
