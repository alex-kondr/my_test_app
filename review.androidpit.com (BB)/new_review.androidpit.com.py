from agent import *
from models.products import *
import time
import random


XCAT = ['[video', 'video]', 'video review']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.inside-digital.de/thema/test', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    time.sleep(random.uniform(1, 3))

    revs = data.xpath('//div[div[contains(@class, "title")]]')
    for rev in revs:
        title = rev.xpath('div[contains(@class, "title")]/a/text()').string()
        cat = rev.xpath('div/a[contains(@class, "category") and not(contains(., "TEST"))]/text()').string()
        url = rev.xpath('div[contains(@class, "title")]/a/@href').string()

        if title and url and not any(xcat in title.lower() for xcat in XCAT):
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url, cat=cat))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    time.sleep(random.uniform(1, 3))

    product = Product()

    product.ssid = context['url'].split('/')[-1].replace('-im-test', '')

    name = data.xpath('//title[contains(text(), " im Test: ")]/text()').string()
    if not name:
        name = context['title']

    product.name = name.split(' im Test: ')[0].split('Durability test: ')[-1].split('[Test]')[-1].split(' test:')[0].split(' Test:')[-1].split(' First Look: ')[0].split('First Look: ')[-1].split(' Review: ')[0].split(' Review: ')[0].split(' Our Review of ')[0].split(' review: ')[0].split(' review: ')[0].split(' Retro-Review: ')[0].split(': hands-on review ')[0].replace('Hands-on review of the ', '').split(' review ')[0].split(' reviewed: ')[0].split(' tested: ')[0].split(' Tested: ')[0].replace(' A Long-Term Review', '').replace('[Hands-On User Review] ', '').replace('AndroidPIT Review Of ', '').replace(' Hands-On Review', '').replace('Testing the ', '').replace('Tested: ', '').replace("? Here's Our Review", '').split(' reviewed in ')[0].split(' re-reviewed: ')[0].split(' review, ')[0].replace(' Review', '').replace('Review of the ', '').replace(' hands-on review', '').replace(' review', '').replace('Hands on: ', '').split('im ersten Test:')[0].split(' im Test:')[0].split(' Test: ')[0].split('im Langzeit-Test:')[0].replace('Netztest:', '').replace('Im Test: ', '').replace(u'im\u00a0Test', '').replace('Testsieger:', '').replace('Test: ', '').replace('PureView', '').strip()

    product.url = data.xpath('//span[contains(@class, "np-offer__link")]/@data-href').string()
    if not product.url:
        product.url = data.xpath('//a[@rel="sponsored"]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(@rel, "sponsored")]/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = context['cat']
    if not product.category:
        product.category = 'Technik'

    review = Review()
    review.title = context['title']
    review.type = 'pro'
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//span[@class="post-date"]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author_name = data.xpath('//div[contains(@class, "author")]/a//text()').string(multiple=True)
    author_url = data.xpath('//div[contains(@class, "author")]/a/@href').string()
    if author_name and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))
    elif author_name:
        review.authors.append(Person(name=author_name, ssid=author_name))

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

    pros = data.xpath('//h3[contains(., "Pros of")]/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('(//h3[contains(., "Vorteile") or contains(., "Pro")]|//h2[contains(., "Pro") and not(contains(., "Contra"))])/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('//p[.//strong[contains(., "Pros")]]/following-sibling::ul[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.replace(u'\uFEFF', '').strip().strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//h3[contains(., "Cons of")]/following-sibling::ul[1]/li')
    if not cons:
        cons = data.xpath('(//h3[contains(., "Nachteile") or contains(., "Contra")]|//h2[contains(., "Contra") and not(contains(., "Pro"))])/following-sibling::ul[1]/li')
    if not cons:
        cons = data.xpath('//p[.//strong[contains(., "Contras") or contains(., "Cons")]]/following-sibling::ul[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.replace(u'\uFEFF', '').strip().strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="post-excerpt"]/p//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//div[@class="post-excerpt"]//text()').string(multiple=True)

    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[strong[contains(., "Conclusion")]]/following-sibling::p[not(contains(., "the device used in this review"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//h2[regexp:test(., "Conclusion|My Thoughts|Final Thoughts|Who should buy|Should You Buy|Final verdict", "i")])[last()]/following-sibling::p[not(contains(., "the device used in this review") or preceding-sibling::h2[contains(., "Where to Buy")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(@id, "fazit") or contains(., "Fazit")]/following-sibling::p[not(contains(., "Contras") or contains(., "Was für das") or contains(., "in Deutschland erhältlich") or contains(., "Gesamtwertung:") or contains(., "Teilwertung:") or contains(., "Pros ") or contains(., "Cons"))]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[strong[contains(., "Conclusion")]]/preceding-sibling::p[not(contains(., "the device used in this review"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[regexp:test(., "Conclusion|My Thoughts|Final Thoughts|Who should buy|Should You Buy|Final verdict", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(@id, "fazit")]/preceding-sibling::p[not(contains(., "Contras") or contains(., "Was für das") or contains(., "in Deutschland erhältlich") or contains(., "Gesamtwertung:") or contains(., "Teilwertung:") or contains(., "Pros ") or contains(., "Cons"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[not(@class or .//span[@class] or contains(., "Contras") or contains(., "Was für das") or contains(., "in Deutschland erhältlich") or contains(., "Gesamtwertung:") or contains(., "Teilwertung:") or contains(., "Pros ") or contains(., "Cons"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="post-content"]/p[not(contains(., "the device used in this review"))]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
