from agent import *
from models.products import *
import re


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.slashgear.com/category/reviews/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if not re.search(r' gift | vs\. | vs ', title.lower(), re.I):
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@id="next-page"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].split(' Review: ')[0].split(' Review: ')[0].split(' Review ')[0].replace(' Reviews', '').replace(' Review', '').strip()
    product.ssid = data.xpath('//h1/@data-post_id').string()
    product.category = 'Tech'

    product.url = data.xpath('//a[contains(., "Amazon")]/@href').string()
    if not product.url:
        product.url = context['url']

    cat = data.xpath('//ul[@class="breadcrumbs"]/li/a[not(contains(@href, "/reviews/"))]/text()').string()
    if cat:
        product.category = cat.replace('Reviews', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "author")]/text()').string()
    author_url = data.xpath('//a[contains(@class, "author")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="score-number"]/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.split('/')[0])
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    pros = data.xpath('//figure[@class="pro"]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.replace(u'\uFEFF', '').strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//figure[@class="con"]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.replace(u'\uFEFF', '').strip(' +-*.:;•,–')
            if len(con) > 1 and 'N/A' not in con:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[regexp:test(., "Verdict", "i")]/following-sibling::div/p[not(regexp:test(., "You can purchase"))]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Verdict", "i")]/preceding::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="columns-holder"]/p[not(@class or regexp:test(., "You can purchase"))]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
