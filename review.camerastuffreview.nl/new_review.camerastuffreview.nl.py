from agent import *
from models.products import *


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers=[SessionBreak(max_requests=10000)]
    session.queue(Request('https://camerastuffreview.com/lenzen/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="elementor-post__title"]/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(url=url))

    next_url = data.xpath('//a[@class="page-numbers next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.ssid = context['url'].split('/')[-2].replace('review-', '')
    product.category = 'Tech'

    title = data.xpath('//meta[@property="og:title"]/@content').string()
    product.name = title.replace('Full review: ', '').replace('Preview: ', '').replace('(P)review: ', '').replace('Review: ', '').split(' – ')[0].split(':')[0].replace('Review ', '').replace('Test ', '').strip()

    product.url = data.xpath('//a[@class="elementor-button elementor-button-link elementor-size-sm"]/@href').string()
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

    author = data.xpath('//meta[@name="author"]/@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//td[contains(., "eindwaardering")]/following-sibling::td/text()').string()
    if grade_overall:
        grade_overall = grade_overall.replace(',', '.').strip(' +-–')
        try:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))
        except:
            pass

    grades = data.xpath('//tr[td[1][regexp:test(., "^[\w/ ]+/\d+$") and not(.//h1 or .//h3)]]')
    for grade in grades:
        grade_name, grade_val = grade.xpath('td')
        grade_name, grade_best = grade_name.xpath('text()').string().split('/')
        grade_val = grade_val.xpath('text()').string()
        if grade_val:
            grade_val = grade_val.replace(',', '.').strip(' +-–')
        try:
            if float(grade_val) > float(grade_best):
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=float(grade_best)+5))
            else:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=float(grade_best)))
        except:
            pass

    pros = data.xpath('//tr[contains(., "VOORDELEN")]/following-sibling::tr/td[1]//li')
    if not pros:
        pros = data.xpath('//h4[contains(., "Voordelen")]/following-sibling::ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' –')
        if pro and len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//tr[contains(., "NADELEN") or contains(., "Nadelen")]/following-sibling::tr/td[2]//li')
    if not cons:
        cons = data.xpath('//h4[contains(., "Nadelen")]/following-sibling::ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(' –')
        if con and len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath('((//div[@class="elementor-widget-container"]/p)[1]|//table[@class="responsive" and not(.//h1 or .//h3)]//p)//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[@data-id="12946e9" or @data-id="97121bd"]//p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//tr[contains(., "Conclusie")]/following-sibling::tr/td/p[not(contains(., "insertgrid") or .//span[@class])]//text()')
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2|//h3)/following-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//table[@class="responsive" and (.//h1 or .//h3)]//td[not(.//h1 or .//h3 or .//h4 or contains(., "insertgrid") or .//span[@class])]//text()[not(contains(., "insertgrid"))]')
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '')

        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
