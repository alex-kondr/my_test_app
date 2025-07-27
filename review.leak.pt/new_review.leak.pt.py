from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.leak.pt/reviews/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="td-module-meta-info"]')
    for rev in revs:
        title = rev.xpath('h3/a/text()').string()
        grade_overall = rev.xpath('count(.//i[@class="td-icon-star"]) + count(.//i[@class="td-icon-star-half"]) div 2')
        url = rev.xpath('h3/a/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, grade_overall=grade_overall, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = re.sub(r'\([\w \-\/]+\)', '', context['title'], count=1, flags=re.UNICODE).replace('Análise – ', '').replace('Review – ', '').replace('Review: ', '').replace('Análise: ', '').split(': ')[0].split(' Review')[0].split(' – ')[0].replace(' review', '').replace('Mini-Review ', '').replace('Análise ', '').replace(' Análise', '').replace('Review ', '').replace('Quick-review ', '').replace('Mini-review ', '').replace('Análise ', '').replace('Análise/', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = 'Tecnologia'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "author-name")]/text()').string()
    author_url = data.xpath('//a[contains(@class, "author-name")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    if context['grade_overall'] and context['grade_overall'] > 0:
        review.grades.append(Grade(type='overall', value=context['grade_overall'], best=5.0))

    if not context['grade_overall']:
        grade_overall = data.xpath('//p[contains(., "Nota final")]//text()').string(multiple=True)
        if grade_overall:
            grade_overall = float(grade_overall.split(':')[-1].split('/')[0].strip())
            review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    pros = data.xpath('(//h4[contains(., "O que este teclado tem de bom?")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h4[contains(., "negativos")]/following-sibling::*)[1]/li')
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
        excerpt = data.xpath('//div[contains(@class, "block-inner")]/p[not(contains(., "Nota final"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
