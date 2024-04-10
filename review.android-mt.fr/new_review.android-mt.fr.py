from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://android-mt.ouest-france.fr/category/appareil/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="entry-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.ssid = context['url'].split('/')[-2]
    product.category = 'Technique'

    product.name = data.xpath('//div[@class="column"]/h2/text()').string()
    if not product.name:
        product.name = context['title'].replace('Promo et test de', '').replace('Test Express :', '').replace('Test EXCLUSIF du', '').replace('Test de', '').replace('Test du', '').replace('[Test ]', '').replace('Test :', '').replace('Test :', '').replace('Test', '').split(':')[0]

    product.url = data.xpath('//a[contains(., "Découvrir l’offre")]/@href').string()
    if not product.url:
        product.url = data.xpath('//p[strong[contains(., "Site")]]/a/@href').string()
    if not product.url:
        product.url = data.xpath('//div[@class="visitappli"]/a[@title]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="author-name"]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="note-g"]/div[@class="number"]/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('//span[@class="review-total-box"]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.split('/')[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//div[@class="note-labo"]/following-sibling::div[@class="fiche-note"]/div[not(contains(., "GÉNÉRAL"))]')
    if not grades:
        grades = data.xpath('//ul[@class="review-list"]/li')
    for grade in grades:
        grade_name = grade.xpath('(div[@class="per"]/h4|strong)/text()').string()
        grade_val = grade.xpath('div[@class="number"]/text()').string()
        if not grade_name:
            grade_name, grade_val = grade.xpath('(.//span)[1]//text()').string(multiple=True).split('-')
            grade_name = grade_name.strip()
            grade_val = grade_val.split('/')[0]

        grade_val = float(grade_val.replace(',', '.').strip('.'))
        review.grades.append(Grade(name=grade_name, value=grade_val, best=10.0))

    summary = data.xpath('//div[@class="excerpt"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    pros = data.xpath('//div[@class="plus"]//li|//h5[contains(., "Les plus")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    pros = data.xpath('//h5[contains(., "Les plus")]/following-sibling::p[not(@class)][1]/text()')
    for pro in pros:
        pro = pro.string(multiple=True).replace('►', '').strip()
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="moins"]//li|//h5[contains(., "Les moins")]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).replace('…', '')
        if con and len(con) > 1:
            review.add_property(type='cons', value=con)

    cons = data.xpath('//h5[contains(., "Les moins")]/following-sibling::p[not(@class)][1]/text()')
    for con in cons:
        con = con.string(multiple=True).replace('►', '').strip()
        review.add_property(type='cons', value=con)

    techniques = data.xpath('//h3[contains(., "techniques")]/following-sibling::p//text()|//p[strong[contains(., "Dimensions")]]//text()').string(multiple=True)

    conclusion = data.xpath('//p[strong[contains(., "verdict")]]/text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//h2[contains(., "verdict")]|//h2[contains(., "Verdict")])/following-sibling::p//text()').string(multiple=True)

    if conclusion:
        if techniques:
            conclusion = conclusion.replace(techniques, '')
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2[contains(., "verdict")]|//h2[contains(., "Verdict")])/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h3[contains(., "techniques")]/preceding-sibling::p[not(strong[contains(., "verdict")])]//text()|//h3[contains(., "techniques")]/preceding-sibling::text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h5[contains(., "Les plus")]/preceding-sibling::p[not(strong[contains(., "verdict")])]//text()|//h5[contains(., "Les plus")]/preceding-sibling::text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h5[contains(., "Les moins")]/preceding-sibling::p[not(strong[contains(., "verdict")])]//text()|//h5[contains(., "Les plus")]/preceding-sibling::text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="pub_pave_article2"]/following-sibling::p[not(strong[contains(., "verdict")])]//text()|//div[@id="pub_pave_article2"]/following-sibling::text()').string(multiple=True)
    if excerpt:
        if techniques:
            excerpt = excerpt.replace(techniques, '')

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
