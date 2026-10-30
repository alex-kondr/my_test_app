from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.whathifi.com/reviews'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//ul[@data-mrf-recirculation="tag-block"]/li')
    for cat in cats:
        name = cat.xpath('h3//text()').string(multiple=True)
        url = cat.xpath('a/@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name, cat_url=url))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    current_page = data.xpath('//span[@class="active"]/text()').string()
    page = context.get('page', 1)
    if not current_page or int(current_page) != page:
        return

    revs = data.xpath('//div[@data-listkey="review"]/div')
    for rev in revs:
        title = rev.xpath('.//div[@class="article-name"]/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_page = page + 1
    next_url = context['cat_url'] + '/page/{}'.format(next_page)
    session.queue(Request(next_url), process_revlist, dict(context, page=next_page))


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].replace(' review', '').strip()
    product.ssid = context['url'].replace('/review', '').split('/')[-1].replace('-review', '')
    product.category = context['cat'].replace('Reviews', '').strip()

    product.url = data.xpath('//a[@rel="sponsored noopener"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[contains(@class, "title")]//text()').string(multiple=True)
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time[@class="relative-date"]/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[contains(@property, "authors")]/@content[not(contains(., "What Hi-Fi?"))]').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count(//div[contains(@class, "verdict")]//span[@class="icon icon-star"]) + count(//div[contains(@class, "verdict")]//span[@class="icon icon-star half"]) div 2')
    if grade_overall:
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    grades = data.xpath('//p[strong[contains(., "SCORES")]]/following-sibling::ul[1]/li[not(contains(., "review"))]')
    if not grades:
        grades = data.xpath('//p[strong[contains(., "SCORES")]]/following-sibling::*[regexp:test(., "\w+ \d+$")]')

    for grade in grades:
        grade_name, grade_val = grade.xpath('.//text()').string(multiple=True).rsplit(' ', 1)
        if grade_name and grade_val and grade_val[0].isdigit():
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('//div[contains(h4, "Reasons to buy")]/ul//p')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(h4, "Reasons to avoid")]/ul//p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="header-sub-container"]/h2[not(@class)]//text()').string(multiple=True)
    if summary:
        summary = summary.replace('&nbsp;', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Verdict")]/following-sibling::p[not(preceding-sibling::p[regexp:test(., "Review published:|SCORES|MORE:")] or regexp:test(., "Review published:|SCORES:|MORE:"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p[not(contains(., "Sound On Sound"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "verdict__verdict")]/p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Verdict")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p[not(preceding-sibling::p[regexp:test(., "Review published:|SCORES|MORE:")] or regexp:test(., "Review published:|SCORES:|MORE:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="article-body"]/p[not(preceding-sibling::p[regexp:test(., "Review published:|SCORES|MORE:")] or regexp:test(., "Review published:|SCORES:|MORE:"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
