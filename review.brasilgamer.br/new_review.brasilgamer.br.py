from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('http://www.brasilgamer.com.br/archive/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="link link--expand"]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[span[@aria-label="Próxima página"]]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.manufacturer = data.xpath('//li[contains(., "Editora:")]/text()').string()

    product.name = context['title'].split(' - ')[0].split(' | ')[0].split(' análise ')[0].replace('pré-review','').replace(' review', '').replace(' Review', '').replace('Análise ao', '').replace('Análise à ','').replace('Análise do ', '').replace('- Análise', '').strip()
    if len(product.name.rsplit(":", 1)[0]) > 3:
        product.name = product.name.rsplit(":", 1)[0].strip()

    category = data.xpath('//li[contains(., "Disponível para")]/text()').string()
    if category:
        product.category = '|'.join(category.replace('|', '/').split(', '))
    else:
        product.category = 'Tecnologia'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="author"]/a/text()').string()
    author_url = data.xpath('//span[@class="author"]/a/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count(//div[@class="review_rating"][1]/span[@class="star"])')
    if grade_overall and grade_overall > 0:
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    if not grade_overall:
        grade_overall = data.xpath('//span[@class="review_rating_value"]/text()').string()
        if not grade_overall:
            grade_overall = data.xpath('//p[contains(., "/10")]/strong/text()').string()
        if grade_overall:
            grade_overall = grade_overall.split('/')[0]
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//td[font[@color="#169600"]]//li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//td[font[@color="#E10000"]]//li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="strapline"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('(//p[strong[contains(., "Conclusão")]]|//h2[contains(., "Conclusão")])/preceding-sibling::p[not(contains(., "Especificações técnicas:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="article_body"]//p[not(contains(., "/10"))]//text()').string(multiple=True)

    next_url = data.xpath('//div[@class="next"]/a/@href').string()
    if next_url:
        page = 1
        title = review.title + " - Pagina " + str(page)
        review.add_property(type='pages', value=dict(title=title, url=review.url))

        session.do(Request(next_url), process_review_next, dict(excerpt=excerpt, review=review, product=product, page=page+1))

    else:
        context['excerpt'] = excerpt
        context['review'] = review
        context['product'] = product

        process_review_next(data, context, session)


def process_review_next(data, context, session):
    review = context['review']

    conclusion = data.xpath('(//p[strong[contains(., "Conclusão")]]|//h2[contains(., "Conclusão")])/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//section[@class="synopsis"]/following-sibling::div[not(@class)]/p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    page = context.get('page', 1)
    if page > 1:
        title = review.title + " - Pagina " + str(page)
        review.add_property(type='pages', value=dict(title=title, url=data.response_url))

        excerpt = data.xpath('(//p[strong[contains(., "Conclusão")]]|//h2[contains(., "Conclusão")])/preceding-sibling::p[not(contains(., "Especificações técnicas:"))]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[@class="article_body"]//p[not(contains(., "/10"))]//text()').string(multiple=True)
        if excerpt:
            if conclusion:
                excerpt = excerpt.replace(conclusion, '').strip()

            context['excerpt'] += " " + excerpt

    next_url = data.xpath('//div[@class="next"]/a/@href').string()
    if next_url:
        session.do(Request(next_url), process_review_next, dict(context, page=page + 1))

    elif context['excerpt']:
        review.add_property(type="excerpt", value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
