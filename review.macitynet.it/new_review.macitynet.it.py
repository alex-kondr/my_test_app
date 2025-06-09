from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.macitynet.it/category/recensioni/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Recensione ', '').split(', ')[0].strip().capitalize()
    product.ssid = context['url'].split('/')[-2].replace('recensione-', '')

    product.url = data.xpath('//a[contains(@href, ".amazon.") or contains(text(), "Amazon")]/@hre').string()
    if not product.url:
        product.url = context['url']

    product.category = data.xpath('//a[contains(@class, "entry-category") and not(contains(., "Recensioni"))]/text()').string()
    if not product.category:
        product.category = 'Tecnologia'

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

    grade_overall = data.xpath('//div[contains(@class, "final-score")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//tr[contains(@class, "row-stars")]')
    for grade in grades:
        grade_name = grade.xpath('td[contains(@class, "review-desc")]/text()').string()
        grade_val = grade.xpath('count(.//i[@class="td-icon-star"]) + count(.//i[@class="td-icon-star-half"]) div 2')
        if grade_name and grade_val > 0:
            review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    pros = data.xpath('//p[strong[contains(., "Pro")]]/following-sibling::ul[1]/li/text()')
    if not pros:
        pros = data.xpath('//h2[span[@id="Pro" or contains(text(), "Pro")]]/following-sibling::p[preceding-sibling::h2[1][span[@id="Pro" or contains(text(), "Pro")]]]/text()')

    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[strong[contains(., "Contro")]]/following-sibling::ul[1]/li/text()')
    if not cons:
        cons = data.xpath('//h2[span[@id="Contro" or contains(text(), "Contro")]]/following-sibling::p[preceding-sibling::h2[1][span[@id="Contro" or contains(text(), "Contro")]]]/text()')

    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "Conclusioni")]/following-sibling::p[not(.//@class="external" or strong[regexp:test(., "Pro|Contro")] or contains(., "•"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusioni")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div/p[not(@class or .//@class="external" or strong[regexp:test(., "Pro|Contro")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
