from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.leak.pt/reviews/', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Análise – ', '').replace('Review – ', '').replace('Review: ', '').replace('Análise: ', '').split(': ')[0].split(' Review')[0].split(' – ')[0].replace(' review', '').replace('Mini-Review ', '').replace('Análise ', '').replace(' Análise', '').replace('Review ', '').replace('Quick-review ', '').replace('Mini-review ', '').replace('Análise ', '').replace('Análise/', '').replace(' (Review)', '').replace('(Análise) ', '').replace('(Review) ', '').replace('(Mini-Review) ', '').replace('(Mini-Análise) ', '').replace('Testámos a ', '').replace('Testámos o ', '').replace('[Review] ', '').replace('[Review/Análise]', '').replace('(Opinião) ', '').replace('(Em análise) ', '').replace('(Quick-Review) ', '').replace('(Re-Review) ', '').replace('(Preview) ', '').replace('(Especial) ', '').replace('(Mini-Teste) ', '').replace('Testei o ', '').replace(' (análise)', '').replace(' (Análise)', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '').replace('-analise', '')

    product.category = data.xpath('//div[contains(@class, "category")]//a[contains(@rel, "tag") and not(regexp:test(., "Tech|Review"))]/text()').string()
    if not product.category:
        product.category = 'Tecnologia'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "author") and span[@class="meta_text" and contains(text(), "por")]]/a[contains(@href, "/author/")]/text()').string()
    author_url = data.xpath('//div[contains(@class, "author") and span[@class="meta_text" and contains(text(), "por")]]/a[contains(@href, "/author/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[contains(., "Nota final")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = float(grade_overall.split(':')[-1].split('/')[0].strip())
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    pros = data.xpath('(//h4[contains(., "O que este teclado tem de bom?")]/following-sibling::*)[1]/li')
    if not pros:
        pros = data.xpath('(//h5[contains(., "Mais concretamente, temos")]/following-sibling::*)[1]/li')
    if not pros:
        pros = data.xpath('(//h3[contains(., "PROS")]/following-sibling::ul)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h4[contains(., "negativos")]/following-sibling::*)[1]/li')
    if not cons:
        cons = data.xpath('(//h5[contains(., "menos positivos")]/following-sibling::*)[1]/li')
    if not cons:
        cons = data.xpath('(//h3[contains(., "CONS")]/following-sibling::ul)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('(//h4|//h3)[regexp:test(., "Conclusão|Vale a pena|veredito|Veredicto", "i")]/following-sibling::p[not(contains(., "Nota final"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('((//h4|//h3)[regexp:test(., "Conclusão|Vale a pena|veredito|Veredicto", "i")])[1]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content-inner")]/p[not(contains(., "Nota final"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
