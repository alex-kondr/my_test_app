from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://gameforfun.com.br/category/reviews/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//a[contains(@class, "link__link")]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].replace('Review ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('review-', '')
    product.category = 'Games'

    platforms = data.xpath('//p[contains(text(), "nos jogos de")]/text()').string()
    if platforms:
        product.category += '|' + platforms.split('nos jogos de')[-1].strip().replace(', ', '/').replace(' e ', '/')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//h2[contains(@class, "heading-title") and contains(., "Por: ")]//text()').string()
    author_url = data.xpath('//h2[contains(@class, "heading-title") and contains(., "Por: ")]/a/@href').string()
    if author and author_url:
        author = author.replace('Por: ', '').strip()
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        author = author.replace('Por: ', '').strip()
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//input[@class="jet-form__field hidden-field" and contains(@name, "_value")]/@value').strings()
    if grade_overall:
        grade_overall = round(sum([float(grade) for grade in grade_overall]) / len(grade_overall))
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//input[@class="jet-form__field hidden-field" and contains(@name, "_value")]')
    for grade in grades:
        grade_name = grade.xpath('@name').string().replace('_value', '').title()
        grade_val = grade.xpath('@value').string()
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100.0))


    pros = data.xpath('(//h3[contains(., "Pros")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[contains(., "Cons")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
