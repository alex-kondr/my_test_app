from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.thetotalsite.it/c/recensioni/recensioni-videogiochi/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="post-title entry-title"]/a')
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(name=name, url=url))


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Games'

    manufacturer = data.xpath('//font[contains(., "Sviluppatore:")]/text()').string()
    if manufacturer:
        product.manufacturer = manufacturer.split(':')[-1].strip()

    platform = data.xpath('//font[contains(., "Piattaforma:") or contains(., "Console:")]/text()').string()
    genre = data.xpath('//font[contains(., "Genere:")]/text()').string()
    if platform and genre:
        product.category = platform.split(':')[-1].strip() + '|' + genre.split(':')[-1].replace(', ', '/').strip()
    elif platform:
        product.category = platform

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="post-inner group"]//a[@rel="author"]/text()').string()
    author_url = data.xpath('//div[@class="post-inner group"]//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[regexp:test(normalize-space(.), "\d+\.?\d? ?/ ?\d+") and contains(., "Globale")]//text()').string(multiple=True)
    if not grade_overall:
        grade_overall = data.xpath('//div[regexp:test(normalize-space(.), "\d+\.?\d? ?/ ?\d+$") and contains(., "Globale")]//text()').string(multiple=True)

    if grade_overall:
        grade_overall = grade_overall.split(':')[-1].split('/')[0].strip()
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//p[regexp:test(normalize-space(.), "\d+\.?\d? ?/ ?\d+") and not(contains(., "Globale"))]')
    for grade in grades:
        grade_name, grade_val = grade.xpath('.//text()').string(multiple=True).split(':')
        grade_val = grade_val.split('/')[0]
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    if not grades:
        grades = data.xpath('//div[regexp:test(normalize-space(.), "\d+\.?\d? ?/ ?\d+$") and not(contains(., "Globale"))]//text()')
        for grade in grades:
            grade_name, grade_val = grade.string(multiple=True).split(':')
            grade_val = grade_val.split('/')[0]
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('//div[not(@class or @id) and contains(., "Pro e contro")]/following-sibling::div[not(@class or @id) and regexp:test(normalize-space(.), "^\+")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' +-–')
        review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//p[not(@class or @id) and contains(., "Pro e contro")]/following-sibling::p[not(@class or @id) and regexp:test(normalize-space(.), "^\+")]/text()')
        for pro in pros:
            pro = pro.string().strip(' +-–')
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[not(@class or @id) and contains(., "Pro e contro")]/following-sibling::div[not(@class or @id) and regexp:test(normalize-space(.), "^–")]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(' +-–')
        review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//p[not(@class or @id) and contains(., "Pro e contro")]/following-sibling::p[not(@class or @id) and regexp:test(normalize-space(.), "^–")]/text()')
        for con in cons:
            con = con.string().strip(' +-–')
            review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@align="center"]//font[@size="3"]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('(//div[@align="center"]/span[@style="font-size: 14pt"])[1]//text()').string(multiple=True)

    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[contains(., "Conclusione")]/following-sibling::p[not(@class or @id or @align or regexp:test(normalize-space(.), "\d+\.?\d?\s?/\s?\d+") or regexp:test(normalize-space(text()), "^\+|^–|^-") or contains(., "Pro e contro"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[contains(., "Conclusione")]/preceding-sibling::p[not(@class or @id or @align or regexp:test(normalize-space(.), "\d+\.?\d?\s?/\s?\d+") or regexp:test(normalize-space(text()), "^\+|^–|^-") or contains(., "Pro e contro"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[not(@class or @id or @align or regexp:test(normalize-space(.), "\d+\.?\d? ?/ ?\d+$"))]/span[@style="color: black"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[not(@class or @id or @align or span or regexp:test(normalize-space(.), "\d+\.?\d? ?/ ?\d+$") or normalize-space(text())="Voti")]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-inner"]/p[not(@class or @id or @align or regexp:test(normalize-space(.), "\d+\.?\d?\s?/\s?\d+") or regexp:test(normalize-space(text()), "^\+|^–|^-") or contains(., "Pro e contro"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
