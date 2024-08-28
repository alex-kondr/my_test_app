from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.inside-digital.de/thema/test'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "td_module_11")]')
    for rev in revs:
        title = rev.xpath('div[contains(@class, "td-module-title")]//a/text()').string()
        cats = rev.xpath('.//a[@class="td-post-category"]/text()[not(contains(., "TEST") or contains(., "1&amp;1") or contains(., "REVIEWS"))]').string()
        url = rev.xpath('div[contains(@class, "td-module-title")]//a/@href').string()
        session.queue(Request(url), process_review, dict(title=title, cats=cats, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('im ersten Test:')[0].split(' im Test:')[0].split(' Test: ')[0].split('im Langzeit-Test:')[0].replace('Netztest:', '').replace('Im Test: ', '').replace(u'im\u00a0Test', '').replace('im Test', '').replace('Testsieger:', '').replace('Test: ', '').replace('PureView', '').strip()
    product.ssid = context['url'].replace('/test', '').replace('/hands-on-test', '').split('/')[-1].replace('-im-test', '')
    product.category = 'Tech'

    product.url = data.xpath('//a[contains(@rel, "sponsored")]/@href').string()
    if not product.url:
        product.url = context['url'].replace('/test', '').replace('/hands-on-test', '')

    if context['cats']:
        product.category = '|'.join([cat.capitalize() for cat in context['cats'].split(', ')]).replace('&amp;', '&').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@itemprop="datePublished"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    grade_overall = data.xpath('//p[.//strong[contains(., "Gesamtwertung:")]]//text()').string(multiple=True)
    if not grade_overall:
        grade_overall = data.xpath('p[.//strong[contains(., "Teilwertung:")]]//text()').string()

    if grade_overall:
        grade_overall = grade_overall.split(':')[-1].split('von')[0].replace(',', '.').replace('Sterne', '').strip()
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//h3[contains(., "Bewertung")]/following-sibling::ul[1]/li[contains(., ":")]')
    for grade in grades:
        grade_name, grade_val = grade.xpath('.//text()').string(multiple=True).split(':')
        grade_name = grade_name.strip()
        grade_val = grade_val.split('von')[0].replace(',', '.').replace('Sterne', '').strip()
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    author = data.xpath('//span[@class="fn"]/a/text()').string()
    author_url = data.xpath('//span[@class="fn"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('(//h3[contains(., "Vorteile") or contains(., "Pro")]|//h2[contains(., "Pro") and not(contains(., "Contra"))])/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('//p[.//strong[contains(., "Pros")]]/following-sibling::ul[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[contains(., "Nachteile") or contains(., "Contra")]|//h2[contains(., "Contra") and not(contains(., "Pro"))])/following-sibling::ul[1]/li')
    if not cons:
        cons = data.xpath('//p[.//strong[contains(., "Contras") or contains(., "Cons")]]/following-sibling::ul[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="post-excerpt"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(@id, "fazit") or contains(., "Fazit")]/following-sibling::p[not(contains(., "Contras") or contains(., "Was für das") or contains(., "in Deutschland erhältlich") or contains(., "Gesamtwertung:") or contains(., "Teilwertung:") or contains(., "Pros ") or contains(., "Cons"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(@id, "fazit")]/preceding-sibling::p[not(contains(., "Contras") or contains(., "Was für das") or contains(., "in Deutschland erhältlich") or contains(., "Gesamtwertung:") or contains(., "Teilwertung:") or contains(., "Pros ") or contains(., "Cons"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[not(@class or .//span[@class] or contains(., "Contras") or contains(., "Was für das") or contains(., "in Deutschland erhältlich") or contains(., "Gesamtwertung:") or contains(., "Teilwertung:") or contains(., "Pros ") or contains(., "Cons"))]//text()').string(multiple=True)

    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)