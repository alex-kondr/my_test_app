from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.whathifi.com/reviews', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[h3[contains(., " Reviews")]]')
    for cat in cats:
        name = cat.xpath('h3/text()').string()
        url = cat.xpath('a/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name, cat_url=url))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//a[@class="article-link"]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, url=url))

    current_page = data.xpath('//span[@class="active"]/text()').string()
    page = context.get('page', 1)
    if current_page and int(current_page) == page:
        next_page = page + 1
        next_url = context['cat_url'] + '/page/{}'.format(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context, page=next_page))


def process_review(data: Response, context: dict[str, str], session: Session):
    title = data.xpath('//h1[contains(@class, "title")]/text()').string()

    product = Product()
    product.name = title.replace(' review', '').strip()
    product.ssid = context['url'].split('/')[-1]
    product.category = context['cat'].replace('Reviews', '').strip()

    product.url = data.xpath('//a[contains(., "Amazon")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(text(), "By")]/a[@rel="author"]/text()').string()
    author_url = data.xpath('//span[contains(text(), "By")]/a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="chunk rating"]/@aria-label').string()
    if grade_overall:
        grade_overall = float(grade_overall.replace('Rating: ', '').split(' out ')[0])
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//p[strong[contains(., "SCORES")]]/following-sibling::ul[1]/li[not(contains(., "review"))]')
    if not grades:
        grades = data.xpath('//p[strong[contains(., "SCORES")]]/following-sibling::*[regexp:test(., "\w+ \d+$")]')

    for grade in grades:
        grade_name, grade_val = grade.xpath('.//text()').string(multiple=True).rsplit(' ', 1)
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('//div[h4[contains(., "Pros")]]/ul/li/p')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[h4[contains(., "Cons")]]/ul/li/p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[not(@id)]/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Verdict")]/following-sibling::p[not(preceding-sibling::p[regexp:test(., "Review published:|SCORES|MORE:")] or regexp:test(., "Review published:|SCORES:|MORE:"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "verdict")]/p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Verdict")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="article-body"]/p[not(preceding-sibling::p[regexp:test(., "Review published:|SCORES|MORE:")] or regexp:test(., "Review published:|SCORES:|MORE:"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
