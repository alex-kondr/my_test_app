from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://falkor-cda.bastian.globo.com/tenants/techtudo/instances/694b2dee-93a8-4065-ac90-41bca2dc88ce/posts/page/1'), process_revlist, {})


def process_revlist(data, context, session):
    data_json = simplejson.loads(data.content)

    revs = data_json.get('items', [])
    for rev in revs:
        title = rev.get('content', {}).get('title')
        prod_id = rev.get('id')
        date = rev.get('publication')
        url = rev.get('content', {}).get('url')
        session.queue(Request(url), process_review, dict(prod_id=prod_id, date=date, title=title, url=url))

    next_page = data_json.get('nextPage')
    if next_page:
        session.queue(Request('https://falkor-cda.bastian.globo.com/tenants/techtudo/instances/694b2dee-93a8-4065-ac90-41bca2dc88ce/posts/page/' + str(next_page)), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review:', '').split(':')[0].split('vale a pena?')[0].replace('Confira a análise de', '').replace('Review', '').replace('em review', '').replace('em Review', '').replace('em análise', '').replace('; veja review', '').replace('; veja teste', '').replace('; confira review', '').replace('; testamos', '').replace('; review', '').replace('Testei o ', '').replace('Análise do ', '').replace('PureView', '').replace('Test ', '').strip()
    product.url = context['url']
    product.ssid = context['prod_id']
    product.category = 'Tecnologia'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    if context['date']:
        review.date = context['date'].split('T')[0]

    author_url = data.xpath('//div[@class="content-publication-data__from"]//a/@href').string()
    author = data.xpath('//div[@class="content-publication-data__from"]//span/text()').string()
    if not author:
        author = data.xpath('//p[@class="content-publication-data__from"]/text()').string()

    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        author = author.replace('; Por TechTudo ', '').replace('Por ', '').strip()
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[animate[@id="score-animate"]]/text()').string(multiple=True)
    if grade_overall:
        grade_overall = float(grade_overall)
        if grade_overall > 10:
            review.grades.append(Grade(type='overall', value=grade_overall, best=100.0))
        else:
            review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    grades = data.xpath('//div[@class="review__attribute"]')
    for grade in grades:
        grade_name = grade.xpath('.//div[@class="review__attribute-name"]//text()').string(multiple=True)
        grade_val = grade.xpath('.//div[@class="review__attribute-score"]//text()').string(multiple=True)
        if grade_val and grade_name:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('//h2[contains(., "Prós")]/following::ul[@class="content-unordered-list"][1]/li')
    if not pros:
        pros = data.xpath('//p[.//span[@itemprop="itemReviewed" and contains(., "Prós")]]/following::ul[@class="content-unordered-list"][1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' +-;*.•')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//h2[.//span[contains(., "Contras")]]/following::ul[@class="content-unordered-list"][1]/li')
    if not cons:
        cons = data.xpath('//p[.//span[@itemprop="itemReviewed" and contains(., "Contras")]]/following::ul[@class="content-unordered-list"][1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(' +-;*.•')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[@class="content-head__subtitle"]/text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    conclusions = data.xpath('//h2[not(@class) and (contains(., "vale a pena") or contains(., "Vale a pena") or contains(., "Conclusão"))]/following::p[contains(@class, "content-text__container") and not(contains(., "Canal do TechTudo") or contains(., "Fórum TechTudo") or contains(., "Com informações de") or contains(., "Prós") or contains(., "Contras") or contains(., "Nota de transparência:") or contains(., "fórum TechTudo"))]//text()').strings()
    if not conclusions:
        conclusions = data.xpath('//p[contains(., "Conclusão")]/following::p[contains(@class, "content-text__container") and not(contains(., "Canal do TechTudo") or contains(., "Fórum TechTudo") or contains(., "Com informações de") or contains(., "Prós") or contains(., "Contras") or contains(., "Nota de transparência:") or contains(., "fórum TechTudo"))]//text()').strings()
    if not conclusions:
        conclusions = data.xpath('//span[@class="review__comment"]//text()').strings()

    if conclusions:
        conclusion = ''.join(conclusions).replace('/&amp;', '').replace('&amp;', '').replace('amp;', '').replace('lt;', '').replace('gt;', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2[contains(., "vale a pena") or contains(., "Vale a pena") or contains(., "Conclusão")]|//p[contains(., "Conclusão")])[1]/preceding::p[contains(@class, "content-text__container") and not(contains(., "Canal do TechTudo") or contains(., "Fórum TechTudo") or contains(., "Com informações de") or contains(., "Prós") or contains(., "Contras") or contains(., "Nota de transparência:") or contains(., "fórum TechTudo"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(@class, "content-text__container") and not(contains(., "Canal do TechTudo") or contains(., "Fórum TechTudo") or contains(., "Com informações de") or contains(., "Prós") or contains(., "Contras") or contains(., "Nota de transparência:") or contains(., "fórum TechTudo"))]//text()').string(multiple=True)

    if excerpt:
        for conclusion in conclusions:
            excerpt = excerpt.replace(conclusion.strip(), '').strip()

        excerpt = excerpt.replace('/&amp;', '').replace('&amp;', '').replace('amp;', '').replace('lt;', '').replace('gt;', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
