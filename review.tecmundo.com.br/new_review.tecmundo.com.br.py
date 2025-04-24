from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.tecmundo.com.br/review/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h4[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    revs_cnt = data.xpath('//span[contains(., " reviews")]/text()').string()
    offset = context.get('offset', 0) + 20
    if revs_cnt:
        revs_cnt = revs_cnt.split(' de ')[-1].split()[0]
        if revs_cnt.isdigit() and int(revs_cnt) > offset:
            next_page = context.get('page', 1) + 1
            next_url = data.response_url.split('?')[0] + '?page=' + str(next_page)
            session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('- Análise')[0].replace("Review -", '')[-1].replace(' - Review', '').split(" Review")[0].split(" review")[0].split("Review:")[-1].split(":")[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].split('-')[0]
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@href, "/autor/") and contains(@class, "link")]/text()').string()
    author_url = data.xpath('//a[contains(@href, "/autor/") and contains(@class, "link")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].split('-')[0]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath("//h3[.//text()[contains(.,'Nota')]]//text()").string(multiple=True)
    if not grade_overall:
        grade_overall = data.xpath("//div[@class='tec--game-rating__value']//text()").string()
    if not grade_overall:
        grade_overall = data.xpath("//h2[.//text()[contains(.,'Nota')]]//text()").string(multiple=True)

    if grade_overall:
        grade_overall = grade_overall.replace('na complexidade', '').split("Nota")[-1].split(":")[-1].split()[-1].replace(',', '')

        if float(grade_overall) <= 10.0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))
        else:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    pros = data.xpath('//h3[regexp:test(., "positivos|prós")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' +-*.:;')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//h3[regexp:test(., "negativos|contras")]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(' +-*.:;')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "tec--article__body")]/p[@dir="ltr"][1]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Vale a pena?")]/following-sibling::p[not(contains(., "Comente nas redes sociais do Voxel"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//h2[contains(., 'VALE A PENA?')]/following-sibling::p[1]//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//h2[contains(., 'Veredito')]/following-sibling::p[1]//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//h2[contains(., 'Conclusão')]/following-sibling::p[1]//text()").string(multiple=True)
    if conclusion:
        conclusion = conclusion.split('---')[0]
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "tec--article__body")]/p[not(span/@data-fonte)][not(.//@data-src)][not(.//img)]//text() | /descendant::ul/li[@dir="ltr"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "tec--article__body")]//p[not(contains(@class, "font-semibold"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@align='justify']//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="tec--article__body"]//div[not(.//img)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="tec--article__body"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@style='text-align:justify']//text()").string(multiple=True)

    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '')
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        excerpt = excerpt.split('---')[0].strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
